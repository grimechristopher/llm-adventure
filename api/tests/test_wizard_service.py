"""
Tests for wizard orchestration service.

These tests verify the wizard flow: starting sessions, responding to questions,
evaluating completeness, and finalizing world creation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from services.world_building_service import WizardOrchestrationService
from db.models import World, WorldGenerationSession
from models.world_building import WizardStartResponse, WizardResponseResponse


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def mock_llm():
    """Create a mock LLM"""
    llm = Mock()
    llm.model_name = "mock-llm"
    return llm


@pytest.fixture
def test_world(mock_db_session):
    """Create a test world"""
    world = World(id=1, name="Test World", description="Test")
    mock_db_session.query(World).filter_by.return_value.first.return_value = world
    return world


def test_service_initialization(mock_db_session, mock_llm):
    """Test wizard service can be initialized"""
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    assert service.db == mock_db_session
    assert service.llm == mock_llm
    assert service.extraction_chain is not None
    assert service.question_chain is not None
    assert service.completion_agent is not None
    assert service.checklist_evaluator is not None


@pytest.mark.asyncio
async def test_start_session_creates_session(mock_db_session, mock_llm, test_world):
    """Test starting a wizard session creates database record"""
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    # Mock the session creation
    def add_side_effect(obj):
        if isinstance(obj, WorldGenerationSession):
            obj.id = 1  # Simulate DB assigning ID

    mock_db_session.add.side_effect = add_side_effect

    response = await service.start_session(world_id=1)

    # Verify response
    assert isinstance(response, WizardStartResponse)
    assert response.session_id == 1
    assert response.first_question is not None
    assert response.stage == 'world_identity'

    # Verify database interaction
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_start_session_world_not_found(mock_db_session, mock_llm):
    """Test starting session with invalid world ID raises error"""
    mock_db_session.query(World).filter_by.return_value.first.return_value = None
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    with pytest.raises(ValueError, match="World .* not found"):
        await service.start_session(world_id=999)


@pytest.mark.asyncio
async def test_respond_extracts_data(mock_db_session, mock_llm, test_world):
    """Test wizard response extracts and stores data"""
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    # Create mock session
    mock_session = WorldGenerationSession(
        id=1,
        world_id=1,
        session_stage='world_identity',
        current_question_type='world_identity',
        gathered_data={'locations': [], 'facts': []}
    )
    mock_db_session.query(WorldGenerationSession).filter_by.return_value.first.return_value = mock_session

    # Mock extraction chain to return structured data
    from models.world_building import WorldBuildingExtraction, LocationCreate, FactCreate
    mock_extraction = WorldBuildingExtraction(
        locations=[LocationCreate(name="TestLoc", description="Test location")],
        facts=[FactCreate(content="Test fact", fact_category="observed")]
    )

    with patch.object(service.extraction_chain, 'ainvoke', return_value=mock_extraction):
        # Mock checklist evaluator
        with patch.object(service.checklist_evaluator, 'evaluate', return_value={
            'overall_complete': False,
            'overall_percentage': 30,
            'satisfied_requirements': [],
            'missing_requirements': ['magic_system', 'technology_level']
        }):
            # Mock question generation
            from models.world_building import WizardQuestionResponse
            mock_question = WizardQuestionResponse(
                question_text="Tell me more about magic?",
                question_type="world_identity",
                context_hint="Need magic system details"
            )

            with patch.object(service.question_chain, 'ainvoke', return_value=mock_question):
                response = await service.respond(
                    session_id=1,
                    response="A high fantasy world with ancient magic"
                )

                # Verify response structure
                assert isinstance(response, WizardResponseResponse)
                assert response.is_complete == False  # Not complete yet
                assert response.next_question is not None

                # Verify data was added to session
                assert len(mock_session.gathered_data['locations']) == 1
                assert len(mock_session.gathered_data['facts']) == 1


@pytest.mark.asyncio
async def test_respond_session_not_found(mock_db_session, mock_llm):
    """Test responding with invalid session ID raises error"""
    mock_db_session.query(WorldGenerationSession).filter_by.return_value.first.return_value = None
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    with pytest.raises(ValueError, match="Session .* not found"):
        await service.respond(session_id=999, response="test")


def test_advance_stage(mock_db_session, mock_llm):
    """Test stage advancement logic"""
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    mock_session = WorldGenerationSession(
        id=1,
        world_id=1,
        session_stage='world_identity',
        current_question_type='world_identity',
        gathered_data={}
    )

    next_stage = service._advance_stage(mock_session)

    assert next_stage == 'locations'
    assert mock_session.session_stage == 'locations'


def test_advance_stage_at_end(mock_db_session, mock_llm):
    """Test advancing stage when already at final stage"""
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    mock_session = WorldGenerationSession(
        id=1,
        world_id=1,
        session_stage='locations',  # Second to last stage
        current_question_type='locations',
        gathered_data={}
    )

    next_stage = service._advance_stage(mock_session)

    assert next_stage == 'complete'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_wizard_full_flow_integration():
    """
    Integration test: Complete wizard flow from start to finalize.

    Run with: pytest -m integration api/tests/test_wizard_service.py

    Requires:
    - PostgreSQL database running
    - LLM API credentials configured
    - Alembic migrations applied
    """
    from config.orm_database import get_db_session
    from config.llm import initialize_llms
    from db.models import World

    db = next(get_db_session())
    llms = initialize_llms()
    llm = llms.get('azure_one')

    if not llm:
        pytest.skip("No LLM configured for integration test")

    # Create test world
    world = World(name="Integration Test World", description="Test")
    db.add(world)
    db.commit()

    try:
        service = WizardOrchestrationService(db, llm)

        # Start session
        start_response = await service.start_session(world.id)
        session_id = start_response.session_id

        assert start_response.first_question is not None
        assert start_response.stage == 'world_identity'

        # Provide detailed response
        detailed_response = """
        This is Aethermoor, a world of floating sky islands.
        Magic is rare and corrupting - it warps reality but destroys the user's mind.
        Technology is medieval with some magical airships.
        The main conflict is falling crystals - bridges between islands are destabilizing.

        Key locations:
        - Skyreach: Central hub city on the largest island
        - Millbrook: Farming community on eastern frontier
        - Ashford: Mining town 78km northeast of Millbrook
        """

        response1 = await service.respond(session_id, detailed_response)

        # Verify extraction happened
        assert len(response1.gathered_so_far.get('locations', [])) >= 3
        assert len(response1.gathered_so_far.get('facts', [])) >= 3

        # If not complete, answer more questions
        while not response1.is_complete and response1.next_question:
            # Provide additional details
            response1 = await service.respond(
                session_id,
                "The sky islands float due to ancient crystal cores. "
                "Society is fragmented - city-states compete for crystals."
            )

        # Finalize (if complete)
        if response1.is_complete:
            finalize_response = await service.finalize(session_id)

            assert finalize_response.locations_created >= 3
            assert finalize_response.facts_created >= 3
            assert finalize_response.world_id == world.id

    finally:
        # Cleanup
        db.query(WorldGenerationSession).filter_by(world_id=world.id).delete()
        db.delete(world)
        db.commit()


@pytest.mark.asyncio
async def test_checklist_evaluation_tracks_progress(mock_db_session, mock_llm, test_world):
    """Test that checklist evaluation tracks requirement satisfaction"""
    service = WizardOrchestrationService(mock_db_session, mock_llm)

    mock_session = WorldGenerationSession(
        id=1,
        world_id=1,
        session_stage='world_identity',
        current_question_type='world_identity',
        gathered_data={'locations': [], 'facts': [], 'checklist_evaluations': []}
    )
    mock_db_session.query(WorldGenerationSession).filter_by.return_value.first.return_value = mock_session

    # Mock extraction and checklist
    from models.world_building import WorldBuildingExtraction, FactCreate

    mock_extraction = WorldBuildingExtraction(
        locations=[],
        facts=[
            FactCreate(content="Magic is rare", fact_category="observed", what_type="cultural"),
            FactCreate(content="Medieval tech level", fact_category="observed", what_type="cultural")
        ]
    )

    checklist_result = {
        'overall_complete': False,
        'overall_percentage': 40,
        'satisfied_requirements': ['magic_system', 'technology_level'],
        'missing_requirements': ['conflict', 'history', 'location_geography']
    }

    with patch.object(service.extraction_chain, 'ainvoke', return_value=mock_extraction):
        with patch.object(service.checklist_evaluator, 'evaluate', return_value=checklist_result):
            with patch.object(service.question_chain, 'ainvoke'):
                await service.respond(session_id=1, response="Test response")

                # Verify checklist evaluation was stored
                assert 'checklist_evaluations' in mock_session.gathered_data
                assert len(mock_session.gathered_data['checklist_evaluations']) > 0

                last_eval = mock_session.gathered_data['checklist_evaluations'][-1]['result']
                assert last_eval['overall_percentage'] == 40
                assert len(last_eval['satisfied_requirements']) == 2

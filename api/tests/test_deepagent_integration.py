"""Tests for DeepAgent integration"""

import pytest
from agents.wizard_completion_agent import create_wizard_completion_agent, completion_parser
from tools import WORLD_BUILDING_TOOLS
from models.world_building import CompletionEvaluation


def test_agent_creation():
    """Verify agent can be created with tools"""
    agent = create_wizard_completion_agent()
    assert agent is not None


def test_world_building_tools_available():
    """Verify all expected tools are available"""
    assert len(WORLD_BUILDING_TOOLS) == 3
    tool_names = [tool.name for tool in WORLD_BUILDING_TOOLS]
    assert 'query_world_facts' in tool_names
    assert 'query_world_locations' in tool_names
    assert 'validate_fact_consistency' in tool_names


def test_completion_parser_exists():
    """Verify completion parser is configured for structured output"""
    assert completion_parser is not None
    assert completion_parser.pydantic_object == CompletionEvaluation


def test_completion_evaluation_model():
    """Test CompletionEvaluation Pydantic model validation"""
    # Valid evaluation
    eval1 = CompletionEvaluation(
        is_complete=True,
        reasoning="World has sufficient detail",
        missing_elements=[],
        vague_responses_detected=[],
        quality_score=0.9,
        next_question_suggestion=None
    )
    assert eval1.is_complete == True
    assert eval1.quality_score == 0.9

    # Invalid quality score (out of range)
    with pytest.raises(Exception):  # Pydantic validation error
        CompletionEvaluation(
            is_complete=False,
            reasoning="Test",
            quality_score=1.5  # Invalid: > 1.0
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_returns_structured_output():
    """
    Integration test: Verify agent returns valid CompletionEvaluation JSON.

    Run with: pytest -m integration api/tests/test_deepagent_integration.py
    """
    agent = create_wizard_completion_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Evaluate this world-building data:

World ID: 1
Stage: world_identity

Gathered Data:
- 2 locations: Millbrook, Ashford
- 3 facts about magic system
- 2 facts about technology

Use query_world_locations and query_world_facts tools to analyze.
Return structured JSON evaluation."""
        }]
    })

    # Extract final message
    final_message = result['messages'][-1]['content']

    # Should be parseable as CompletionEvaluation
    evaluation = completion_parser.parse(final_message)

    assert isinstance(evaluation, CompletionEvaluation)
    assert isinstance(evaluation.is_complete, bool)
    assert isinstance(evaluation.reasoning, str)
    assert isinstance(evaluation.quality_score, float)
    assert 0.0 <= evaluation.quality_score <= 1.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_wizard_completion_with_deepagent():
    """
    Integration test: DeepAgent in wizard flow detects vague responses.

    Requires:
    - Database setup
    - LLM API configured
    """
    from config.orm_database import get_db_session
    from config.llm import initialize_llms
    from db.models import World, WorldGenerationSession
    from services.world_building_service import WizardOrchestrationService

    db = next(get_db_session())
    llms = initialize_llms()
    llm = llms.get('azure_one')

    if not llm:
        pytest.skip("No LLM configured for integration test")

    # Create test world
    world = World(name="Vague Test World", description="Test")
    db.add(world)
    db.commit()

    try:
        service = WizardOrchestrationService(db, llm)
        start_response = await service.start_session(world.id)

        # Simulate user providing vague response
        await service.respond(start_response.session_id, "A fantasy world with magic")

        # Check if DeepAgent detected vagueness
        wizard_session = db.query(WorldGenerationSession).get(start_response.session_id)
        is_complete = await service._is_stage_complete(wizard_session)

        # Should NOT be complete (vague response)
        assert is_complete == False, "DeepAgent should detect vague response"

        # Check if DeepAgent evaluation was stored
        deepagent_evals = wizard_session.gathered_data.get('deepagent_evaluations', [])
        if deepagent_evals:
            latest = deepagent_evals[-1]['evaluation']
            assert latest['quality_score'] < 0.5, "Vague response should have low quality score"
            assert len(latest['vague_responses_detected']) > 0, "Should detect vagueness"

    finally:
        # Cleanup
        db.query(WorldGenerationSession).filter_by(world_id=world.id).delete()
        db.delete(world)
        db.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_wizard_completion_detects_quality():
    """
    Integration test: DeepAgent detects high-quality detailed responses.

    Requires:
    - Database setup
    - LLM API configured
    """
    from config.orm_database import get_db_session
    from config.llm import initialize_llms
    from db.models import World, WorldGenerationSession
    from services.world_building_service import WizardOrchestrationService

    db = next(get_db_session())
    llms = initialize_llms()
    llm = llms.get('azure_one')

    if not llm:
        pytest.skip("No LLM configured for integration test")

    # Create test world
    world = World(name="Quality Test World", description="Test")
    db.add(world)
    db.commit()

    try:
        service = WizardOrchestrationService(db, llm)
        start_response = await service.start_session(world.id)

        # Provide detailed, high-quality response
        detailed_response = """
        This is Aethermoor, a world of floating sky islands connected by ancient crystal bridges.
        Magic here is rare and corrupting - it warps reality but slowly destroys the user's mind.
        The technology level is similar to late medieval with some magical airships powered by crystal shards.
        The major conflict is the falling crystals - the bridges between islands are destabilizing,
        threatening to isolate communities. The great sky empire collapsed 500 years ago when
        their capital island fell. Now independent city-states compete for dwindling crystal resources.

        Key locations:
        - Skyreach: The central hub city built on the largest sky island
        - Millbrook: A quiet farming community on the eastern frontier
        - Ashford: A mining town 78km northeast of Millbrook, known for crystal extraction
        """

        await service.respond(start_response.session_id, detailed_response)

        # Check that requirements are satisfied
        wizard_session = db.query(WorldGenerationSession).get(start_response.session_id)
        checklist_evals = wizard_session.gathered_data.get('checklist_evaluations', [])

        assert len(checklist_evals) > 0, "Should have checklist evaluation"
        latest_eval = checklist_evals[-1]['result']
        assert latest_eval['overall_percentage'] > 50, "Detailed response should satisfy many requirements"

        # Check if high-quality detail is reflected in DeepAgent evaluation
        deepagent_evals = wizard_session.gathered_data.get('deepagent_evaluations', [])
        if deepagent_evals:
            latest = deepagent_evals[-1]['evaluation']
            assert latest['quality_score'] > 0.5, "Detailed response should have high quality score"

    finally:
        # Cleanup
        db.query(WorldGenerationSession).filter_by(world_id=world.id).delete()
        db.delete(world)
        db.commit()

"""
Tests for world builder agent extraction chains.

These tests verify that the LangChain LCEL chains properly extract
structured data from natural language descriptions.
"""

import pytest
from agents.world_builder import (
    create_world_builder_chain,
    create_wizard_question_chain,
    create_relative_position_parser_chain,
    validate_extraction_result,
    get_extraction_statistics
)
from models.world_building import WorldBuildingExtraction


class MockLLM:
    """Mock LLM for testing chains without API calls"""

    def __init__(self, response: str):
        self.response = response
        self.model_name = "mock-llm"

    def invoke(self, prompt):
        """Return mock response"""
        return MockMessage(self.response)

    async def ainvoke(self, prompt):
        """Async version of invoke"""
        return self.invoke(prompt)


class MockMessage:
    """Mock message response"""

    def __init__(self, content: str):
        self.content = content


def test_world_builder_chain_creation():
    """Test that world builder chain can be created"""
    mock_llm = MockLLM('{"locations": [], "facts": []}')
    chain, parser = create_world_builder_chain(mock_llm)

    assert chain is not None
    assert parser is not None
    assert parser.pydantic_object == WorldBuildingExtraction


def test_extraction_validation_empty():
    """Test validation rejects empty extraction results"""
    result = WorldBuildingExtraction(locations=[], facts=[])
    assert validate_extraction_result(result) == False


def test_extraction_validation_with_location():
    """Test validation passes with at least one location"""
    from models.world_building import LocationCreate

    result = WorldBuildingExtraction(
        locations=[LocationCreate(
            name="Millbrook",
            description="A small farming village"
        )],
        facts=[]
    )
    assert validate_extraction_result(result) == True


def test_extraction_validation_duplicate_names():
    """Test validation detects duplicate location names"""
    from models.world_building import LocationCreate

    result = WorldBuildingExtraction(
        locations=[
            LocationCreate(name="Millbrook", description="Village"),
            LocationCreate(name="millbrook", description="Same village")  # Duplicate (case-insensitive)
        ],
        facts=[]
    )
    assert validate_extraction_result(result) == False


def test_extraction_statistics():
    """Test extraction statistics generation"""
    from models.world_building import LocationCreate, FactCreate

    result = WorldBuildingExtraction(
        locations=[
            LocationCreate(
                name="Millbrook",
                description="Village",
                relative_position="north of Capital",
                elevation_meters=500
            ),
            LocationCreate(
                name="Ashford",
                description="Mining town"
            )
        ],
        facts=[
            FactCreate(
                content="Millbrook has 200 residents",
                fact_category="observed",
                what_type="demographic",
                location_name="Millbrook"
            ),
            FactCreate(
                content="Founded 50 years ago",
                fact_category="historical",
                what_type="demographic"
            )
        ]
    )

    stats = get_extraction_statistics(result)

    assert stats['total_locations'] == 2
    assert stats['total_facts'] == 2
    assert stats['locations_with_position'] == 1
    assert stats['locations_with_elevation'] == 1
    assert stats['facts_linked_to_locations'] == 1
    assert 'observed' in stats['fact_categories']
    assert 'historical' in stats['fact_categories']
    assert stats['fact_categories']['observed'] == 1
    assert stats['fact_categories']['historical'] == 1


def test_wizard_question_chain_creation():
    """Test wizard question chain can be created"""
    mock_llm = MockLLM('{"question_text": "Test?", "question_type": "test", "context_hint": "testing"}')
    chain, parser = create_wizard_question_chain(mock_llm)

    assert chain is not None
    assert parser is not None


def test_relative_position_parser_chain_creation():
    """Test relative position parser chain can be created"""
    mock_llm = MockLLM('{"reference_location_name": "Capital", "direction": "north", "distance_qualifier": "far", "additional_constraints": []}')
    chain, parser = create_relative_position_parser_chain(mock_llm)

    assert chain is not None
    assert parser is not None


# Integration tests (require LLM API access)
# These are marked with pytest.mark.integration and can be run separately

@pytest.mark.integration
@pytest.mark.asyncio
async def test_extraction_integration():
    """
    Integration test: Full extraction chain with real LLM.

    Run with: pytest -m integration api/tests/test_world_builder_agent.py

    Requires:
    - LLM API credentials configured in .env
    """
    from config.llm import initialize_llms

    llms = initialize_llms()
    llm = llms.get('azure_one')  # Or whichever LLM you have configured

    if not llm:
        pytest.skip("No LLM configured for integration test")

    chain, parser = create_world_builder_chain(llm)

    description = """
    Millbrook is a small farming village nestled in a valley, population around 200.
    The village was founded 50 years ago by settlers from the capital.
    To the northeast, about 78 kilometers away, lies Ashford, a mining town known for crystal extraction.
    """

    result = await chain.ainvoke({"description": description})

    # Verify extraction worked
    assert isinstance(result, WorldBuildingExtraction)
    assert len(result.locations) >= 2  # Should extract Millbrook and Ashford
    assert len(result.facts) >= 2  # Should extract population, founding, distance

    # Verify location names
    location_names = [loc.name for loc in result.locations]
    assert "Millbrook" in location_names or "millbrook" in location_names.lower()

    # Verify facts are categorized
    assert all(fact.fact_category in ['observed', 'historical', 'current_state', 'deduction', 'measurement']
               for fact in result.facts)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_relative_position_parsing_integration():
    """Integration test: Relative position parsing with real LLM"""
    from config.llm import initialize_llms

    llms = initialize_llms()
    llm = llms.get('azure_one')

    if not llm:
        pytest.skip("No LLM configured for integration test")

    chain, parser = create_relative_position_parser_chain(llm)

    test_cases = [
        "far north of the Capital",
        "on the coast, east of the mountains",
        "between Millbrook and Ashford"
    ]

    for position_text in test_cases:
        result = await chain.ainvoke({"relative_position": position_text})

        # Verify result has expected fields
        assert hasattr(result, 'reference_location_name')
        assert hasattr(result, 'direction')
        assert hasattr(result, 'distance_qualifier')
        assert hasattr(result, 'additional_constraints')

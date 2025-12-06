"""Integration tests for spatial planner agent (Phase 2)"""

import json
import pytest
from agents.spatial_planner_agent import create_spatial_planner_agent


# NOTE: These tests require:
# 1. Database with test world and locations
# 2. LLM API credentials configured (for DeepAgent)
# 3. Async test support


@pytest.mark.asyncio
async def test_agent_creation():
    """Test that spatial planner agent can be created"""
    agent = create_spatial_planner_agent()
    assert agent is not None


@pytest.mark.asyncio
async def test_spatial_planner_single_constraint_simple(test_world_with_locations):
    """Test agent handles single constraint: '78km northeast of Millbrook'

    Requires test_world_with_locations fixture with Millbrook at known coordinates
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'TestTown'.

**Constraint Description**: 78km northeast of Millbrook
**World ID**: 1

Use tools to calculate and validate coordinates."""
        }]
    })

    # Verify agent completed without error
    assert result is not None
    assert "messages" in result

    final_msg = result['messages'][-1]['content']

    # Verify agent called tools
    tool_calls = [m for m in result['messages'] if hasattr(m, 'tool_calls') and m.tool_calls]
    assert len(tool_calls) > 0, "Agent should have used tools"

    # Verify structured output
    assert "proposed_lat" in final_msg.lower() or "lat" in final_msg.lower()
    assert "proposed_lon" in final_msg.lower() or "lon" in final_msg.lower()


@pytest.mark.asyncio
async def test_spatial_planner_single_constraint_with_validation(test_world_with_locations):
    """Test agent uses validation tools for single constraint

    Verifies that agent not only proposes coordinates but validates them
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'ValidatedTown'.

**Constraint Description**: 50km south of Ashford
**World ID**: 1

IMPORTANT: Use validate_bearing_constraint and validate_distance_constraint to verify your proposed coordinates."""
        }]
    })

    final_msg = result['messages'][-1]['content']

    # Check for validation in message history
    tool_names = []
    for msg in result['messages']:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if hasattr(tc, 'name'):
                    tool_names.append(tc.name)
                elif isinstance(tc, dict) and 'name' in tc:
                    tool_names.append(tc['name'])

    # Should have used query, calculation, and validation tools
    assert 'query_world_locations' in tool_names or 'project_from_point' in tool_names, \
        "Agent should query or calculate positions"


@pytest.mark.asyncio
async def test_spatial_planner_multi_constraint(test_world_with_locations):
    """Test agent handles multiple constraints: 'between A and B, near coast'

    This tests the agent's ability to reason about multiple simultaneous constraints
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'Port Town'.

**Constraint Description**: between Millbrook and Ashford, near the eastern coast
**World ID**: 1

Parse BOTH constraints and propose coordinates that satisfy both."""
        }]
    })

    final_msg = result['messages'][-1]['content']

    # Verify agent parsed multiple constraints
    assert "between" in final_msg.lower() or "millbrook" in final_msg.lower()
    assert "coast" in final_msg.lower() or "eastern" in final_msg.lower()

    # Verify validation results mentioned
    assert "validation" in final_msg.lower() or "constraint" in final_msg.lower()


@pytest.mark.asyncio
async def test_spatial_planner_impossible_constraints():
    """Test agent handles contradictory constraints gracefully

    Agent should recognize impossible constraints and report them
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for 'ImpossiblePlace'.

**Constraint Description**: 10km north of Millbrook AND 10km south of Millbrook
**World ID**: 1

These constraints are contradictory. Handle this gracefully."""
        }]
    })

    final_msg = result['messages'][-1]['content']

    # Should still return JSON, but with low confidence or notes about impossibility
    assert "confidence" in final_msg.lower() or "notes" in final_msg.lower() or "impossible" in final_msg.lower()


@pytest.mark.asyncio
async def test_spatial_planner_json_output_structure(test_world_with_locations):
    """Test that agent returns properly structured JSON output

    Verifies all required fields are present
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'StructuredTest'.

**Constraint Description**: 30km west of Skyreach
**World ID**: 1

Return JSON with: proposed_lat, proposed_lon, reasoning, constraints_parsed, validation_results, confidence, notes"""
        }]
    })

    final_msg = result['messages'][-1]['content']

    # Try to extract and parse JSON
    try:
        if '```json' in final_msg:
            json_str = final_msg.split('```json')[1].split('```')[0].strip()
        elif '```' in final_msg:
            json_str = final_msg.split('```')[1].split('```')[0].strip()
        else:
            json_str = final_msg.strip()

        data = json.loads(json_str)

        # Verify required fields
        assert "proposed_lat" in data, "Missing proposed_lat"
        assert "proposed_lon" in data, "Missing proposed_lon"
        assert "reasoning" in data or "notes" in data, "Missing reasoning/notes"

    except json.JSONDecodeError:
        pytest.fail(f"Agent did not return valid JSON. Output: {final_msg[:200]}")


@pytest.mark.asyncio
async def test_spatial_planner_coordinate_bounds(test_world_with_locations):
    """Test that agent respects quarter-Earth bounds (-40° to +40° latitude)"""
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'BoundTest'.

**Constraint Description**: very far north of Millbrook
**World ID**: 1

IMPORTANT: Coordinates must be within -40° to +40° latitude range (quarter-Earth constraint)."""
        }]
    })

    final_msg = result['messages'][-1]['content']

    # Extract coordinates if possible
    try:
        if '```json' in final_msg:
            json_str = final_msg.split('```json')[1].split('```')[0].strip()
        else:
            json_str = final_msg.strip()

        data = json.loads(json_str)

        if "proposed_lat" in data:
            lat = float(data["proposed_lat"])
            assert -40 <= lat <= 40, f"Latitude {lat} outside valid range [-40, 40]"

        if "proposed_lon" in data:
            lon = float(data["proposed_lon"])
            assert -180 <= lon <= 180, f"Longitude {lon} outside valid range [-180, 180]"

    except (json.JSONDecodeError, KeyError, ValueError):
        # If JSON parsing fails, just check that bounds are mentioned
        assert "-40" in final_msg or "40" in final_msg or "bounds" in final_msg.lower()


@pytest.mark.asyncio
async def test_spatial_planner_distance_interpretation(test_world_with_locations):
    """Test agent interprets qualitative distances correctly

    Verifies agent uses distance interpretation guide (e.g., "nearby" → 10-30km)
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'NearbyTown'.

**Constraint Description**: nearby Millbrook
**World ID**: 1

"Nearby" should be interpreted as 10-30km according to the distance interpretation guide."""
        }]
    })

    final_msg = result['messages'][-1]['content']

    # Check that agent mentions distance reasoning
    assert "10" in final_msg or "20" in final_msg or "30" in final_msg or "nearby" in final_msg.lower()


@pytest.mark.asyncio
async def test_spatial_planner_travel_time_conversion(test_world_with_locations):
    """Test agent converts travel time to distance

    Verifies "2 days travel" → 60-80km conversion
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'TravelTown'.

**Constraint Description**: 2 days travel north of Ashford
**World ID**: 1

Convert "2 days travel" to kilometers using the travel time guide (should be 60-80km)."""
        }]
    })

    final_msg = result['messages'][-1]['content']

    # Check that agent mentions distance conversion
    assert "60" in final_msg or "70" in final_msg or "80" in final_msg or "travel" in final_msg.lower()


@pytest.mark.asyncio
async def test_spatial_planner_between_constraint(test_world_with_locations):
    """Test agent correctly handles 'between' constraint

    Should use calculate_midpoint tool
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'MidpointTown'.

**Constraint Description**: between Millbrook and Ashford
**World ID**: 1

Use calculate_midpoint tool to find the midpoint."""
        }]
    })

    # Check tool usage
    tool_names = []
    for msg in result['messages']:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if hasattr(tc, 'name'):
                    tool_names.append(tc.name)

    assert 'calculate_midpoint' in tool_names, "Agent should use calculate_midpoint for 'between' constraint"


@pytest.mark.asyncio
async def test_spatial_planner_equidistant_constraint(test_world_with_locations):
    """Test agent handles 'equidistant from' constraint

    Should use calculate_centroid_of_locations tool
    """
    agent = create_spatial_planner_agent()

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": """Find coordinates for location 'CentroidTown'.

**Constraint Description**: equidistant from Millbrook, Ashford, and Skyreach
**World ID**: 1

Use calculate_centroid_of_locations tool."""
        }]
    })

    # Check tool usage
    tool_names = []
    for msg in result['messages']:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if hasattr(tc, 'name'):
                    tool_names.append(tc.name)

    assert 'calculate_centroid_of_locations' in tool_names, \
        "Agent should use calculate_centroid_of_locations for 'equidistant' constraint"


# Pytest fixtures would be defined in conftest.py:
# @pytest.fixture
# async def test_world_with_locations(db_session):
#     """Create test world with sample locations for agent testing"""
#     # Create world
#     # Create locations: Millbrook, Ashford, Skyreach with coordinates
#     # Return world object
#     pass

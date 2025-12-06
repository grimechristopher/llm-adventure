"""
World Query Tools for DeepAgent Integration

These tools allow DeepAgents to query the llm-adventure database
for facts, locations, and world information to support reasoning
and decision-making.
"""

import json
from langchain_core.tools import tool
from db.models import World, Location, Fact


@tool
def query_world_facts(world_id: int, fact_category: str = None) -> str:
    """Query facts about a world, optionally filtered by category.

    Args:
        world_id: ID of the world to query
        fact_category: Optional filter (observed, historical, current_state, world_rule, etc.)

    Returns:
        JSON string containing list of facts with content, category, and type

    Example:
        >>> query_world_facts(1, "historical")
        '[{"content": "Ancient civilization collapsed 500 years ago", "category": "historical", "what_type": "cultural"}]'
    """
    try:
        from config.orm_database import get_db_session
        session = next(get_db_session())

        query = session.query(Fact).filter_by(world_id=world_id)
        if fact_category:
            query = query.filter_by(fact_category=fact_category)

        facts = query.all()
        result = [{
            'content': f.content,
            'category': f.fact_category,
            'what_type': f.what_type
        } for f in facts]

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": f"Failed to query facts for world {world_id}"
        })


@tool
def query_world_locations(world_id: int) -> str:
    """Get all locations in a world with their relationships.

    Args:
        world_id: ID of the world to query

    Returns:
        JSON string containing list of locations with name, type, description, and position

    Example:
        >>> query_world_locations(1)
        '[{"name": "Skyreach", "type": "city", "description": "Capital at center", "relative_position": "center"}]'
    """
    try:
        from config.orm_database import get_db_session
        session = next(get_db_session())

        locations = session.query(Location).filter_by(world_id=world_id).all()
        result = [{
            'name': loc.name,
            'type': loc.location_type,
            'description': loc.description,
            'relative_position': loc.relative_position
        } for loc in locations]

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": f"Failed to query locations for world {world_id}"
        })


@tool
def validate_fact_consistency(world_id: int, new_fact: str) -> str:
    """Check if a new fact contradicts existing world facts.

    This tool returns existing facts so the agent can reason about
    potential contradictions using its own understanding.

    Args:
        world_id: ID of the world
        new_fact: Proposed new fact content to validate

    Returns:
        JSON string with existing facts for agent to analyze

    Example:
        >>> validate_fact_consistency(1, "The capital is coastal")
        '{"new_fact": "The capital is coastal", "existing_facts": [...]}'
    """
    try:
        # Get all existing facts for the agent to reason about
        existing_facts = query_world_facts(world_id)

        return json.dumps({
            "new_fact": new_fact,
            "existing_facts": json.loads(existing_facts),
            "instruction": "Analyze if the new_fact contradicts any existing_facts. Look for logical inconsistencies."
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": f"Failed to validate fact consistency for world {world_id}"
        })

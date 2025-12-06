"""Domain-specific tools for DeepAgent integration"""

from .world_query import query_world_facts, query_world_locations, validate_fact_consistency
from .spatial_calculator import (
    calculate_distance,
    calculate_bearing,
    find_coordinates_for_constraints,
    # Phase 2 tools:
    calculate_midpoint,
    calculate_centroid_of_locations,
    validate_bearing_constraint,
    validate_distance_constraint,
    find_nearby_locations,
    project_from_point
)

# Tool collections for different agent types
WORLD_BUILDING_TOOLS = [
    query_world_facts,
    query_world_locations,
    validate_fact_consistency
]

SPATIAL_REASONING_TOOLS = [
    query_world_locations,
    calculate_distance,
    calculate_bearing,
    find_coordinates_for_constraints,
    # Phase 2 tools:
    calculate_midpoint,
    calculate_centroid_of_locations,
    validate_bearing_constraint,
    validate_distance_constraint,
    find_nearby_locations,
    project_from_point
]

ALL_TOOLS = WORLD_BUILDING_TOOLS + SPATIAL_REASONING_TOOLS

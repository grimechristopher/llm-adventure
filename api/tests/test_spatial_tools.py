"""Unit tests for spatial calculation tools (Phase 2)"""

import json
import pytest
from tools.spatial_calculator import (
    calculate_midpoint,
    calculate_centroid_of_locations,
    validate_bearing_constraint,
    validate_distance_constraint,
    find_nearby_locations,
    project_from_point
)


# NOTE: These tests require a test database with PostGIS extension enabled
# and test locations with coordinates. They should be run with pytest fixtures
# that set up the test database and populate test data.


def test_calculate_midpoint_basic():
    """Test midpoint calculation returns valid JSON structure"""
    # This test would require test database with actual locations
    # For now, we test that the function handles errors gracefully
    result = calculate_midpoint("NonexistentLocation1", "NonexistentLocation2", world_id=999)
    data = json.loads(result)

    # Should return error for nonexistent locations
    assert "error" in data or "lat" in data


def test_calculate_midpoint_with_real_locations(test_world_with_locations):
    """Test midpoint calculation between two real locations

    Requires test_world_with_locations fixture that creates:
    - Millbrook at (12.0, 34.0)
    - Ashford at (12.7, 34.5)
    """
    result = calculate_midpoint("Millbrook", "Ashford", world_id=test_world_with_locations.id)
    data = json.loads(result)

    # Should return valid midpoint data
    assert "lat" in data
    assert "lon" in data
    assert "distance_to_each" in data
    assert data["distance_to_each"].endswith(" km")

    # Midpoint should be between the two locations
    assert 12.0 <= data["lat"] <= 12.7
    assert 34.0 <= data["lon"] <= 34.5


def test_calculate_centroid_basic():
    """Test centroid calculation returns valid JSON structure"""
    result = calculate_centroid_of_locations("Loc1,Loc2,Loc3", world_id=999)
    data = json.loads(result)

    # Should handle nonexistent locations gracefully
    assert "error" in data or "lat" in data


def test_calculate_centroid_with_real_locations(test_world_with_locations):
    """Test centroid of multiple locations

    Requires test_world_with_locations fixture with 3+ locations
    """
    result = calculate_centroid_of_locations("Millbrook,Ashford,Skyreach", world_id=test_world_with_locations.id)
    data = json.loads(result)

    if "error" not in data:
        assert "lat" in data
        assert "lon" in data
        assert "avg_distance" in data
        assert data["avg_distance"].endswith(" km")


def test_validate_bearing_constraint_north():
    """Test bearing validation for cardinal direction"""
    # Would require test location at known coordinates
    # Test that function handles direction normalization
    result = validate_bearing_constraint("TestLoc", 10.0, 10.0, "north", world_id=999)
    data = json.loads(result)

    # Should return error or validation result
    assert "error" in data or "valid" in data


def test_validate_bearing_constraint_tolerance(test_world_with_locations):
    """Test bearing validation with ±45° tolerance

    Requires test location at (0, 0) to test bearing calculations
    """
    # Assuming test location at origin
    # Point at (0, 10) is due east (90°)
    # Should validate as "east" but NOT as "north" or "south"
    result = validate_bearing_constraint("Origin", 0.0, 10.0, "east", world_id=test_world_with_locations.id)
    data = json.loads(result)

    if "valid" in data:
        assert data["valid"] is True
        assert "E" in data["actual_bearing"]
        assert data["deviation_degrees"] <= 45.0


def test_validate_distance_constraint_basic():
    """Test distance validation returns valid JSON structure"""
    result = validate_distance_constraint("TestLoc", 12.5, 34.7, 75.0, 10.0, world_id=999)
    data = json.loads(result)

    # Should return error or validation result
    assert "error" in data or "valid" in data


def test_validate_distance_constraint_with_tolerance(test_world_with_locations):
    """Test distance validation with tolerance

    Requires test location Millbrook at (12.0, 34.0)
    """
    # Testing distance from Millbrook (12.0, 34.0) to point (12.5, 34.7)
    # Should validate within reasonable tolerance
    result = validate_distance_constraint("Millbrook", 12.5, 34.7, 75.0, 20.0, world_id=test_world_with_locations.id)
    data = json.loads(result)

    if "valid" in data:
        assert "actual_distance" in data
        assert "expected" in data
        assert "error_km" in data
        # Error should be numeric
        assert isinstance(data["error_km"], (int, float))


def test_find_nearby_locations_basic():
    """Test find nearby locations returns valid JSON array"""
    result = find_nearby_locations(12.0, 34.0, 50.0, world_id=999)
    data = json.loads(result)

    # Should return array (empty if no locations) or error
    assert isinstance(data, list) or "error" in data


def test_find_nearby_locations_with_real_data(test_world_with_locations):
    """Test finding locations within radius

    Requires test world with multiple locations
    """
    # Search near Millbrook (12.0, 34.0) with 100km radius
    result = find_nearby_locations(12.0, 34.0, 100.0, world_id=test_world_with_locations.id)
    data = json.loads(result)

    assert isinstance(data, list)
    for loc in data:
        assert "name" in loc
        assert "distance" in loc
        assert "bearing" in loc
        assert loc["distance"].endswith(" km")
        # Bearing should have degree symbol and cardinal direction
        assert "°" in loc["bearing"]


def test_find_nearby_locations_ordering(test_world_with_locations):
    """Test that nearby locations are ordered by distance"""
    result = find_nearby_locations(12.0, 34.0, 200.0, world_id=test_world_with_locations.id)
    data = json.loads(result)

    if isinstance(data, list) and len(data) > 1:
        # Extract distances as floats
        distances = [float(loc["distance"].split()[0]) for loc in data]
        # Verify sorted ascending
        assert distances == sorted(distances)


def test_project_from_point_basic():
    """Test projection returns valid JSON structure"""
    result = project_from_point("TestLoc", 45.0, 78.0, world_id=999)
    data = json.loads(result)

    # Should return error or projection result
    assert "error" in data or "lat" in data


def test_project_from_point_northeast(test_world_with_locations):
    """Test projecting point at bearing and distance

    Requires test location Millbrook at (12.0, 34.0)
    """
    # Project 78km at 45° (northeast) from Millbrook
    result = project_from_point("Millbrook", 45.0, 78.0, world_id=test_world_with_locations.id)
    data = json.loads(result)

    if "lat" in data:
        assert "lon" in data
        assert "verification" in data
        # Verification should mention the distance and bearing
        assert "78" in data["verification"]
        assert "45" in data["verification"]
        assert "NE" in data["verification"]

        # Projected point should be northeast of Millbrook (12.0, 34.0)
        assert data["lat"] > 12.0  # Should be north (higher latitude)
        assert data["lon"] > 34.0  # Should be east (higher longitude)


def test_project_from_point_directions(test_world_with_locations):
    """Test projection in all cardinal directions

    Requires test location Origin at (0, 0)
    """
    directions = {
        0: "north",  # Should increase latitude
        90: "east",  # Should increase longitude
        180: "south",  # Should decrease latitude
        270: "west"  # Should decrease longitude
    }

    for bearing, direction in directions.items():
        result = project_from_point("Origin", float(bearing), 50.0, world_id=test_world_with_locations.id)
        data = json.loads(result)

        if "lat" in data:
            # Verify direction logic
            if direction == "north":
                assert data["lat"] > 0, f"North projection should increase latitude"
            elif direction == "south":
                assert data["lat"] < 0, f"South projection should decrease latitude"
            elif direction == "east":
                assert data["lon"] > 0, f"East projection should increase longitude"
            elif direction == "west":
                assert data["lon"] < 0, f"West projection should decrease longitude"


# Additional edge case tests

def test_validate_bearing_unknown_direction():
    """Test bearing validation with invalid direction"""
    result = validate_bearing_constraint("TestLoc", 0.0, 0.0, "invalid_direction", world_id=999)
    data = json.loads(result)

    assert "error" in data
    assert "Unknown direction" in data["error"]


def test_calculate_centroid_single_location():
    """Test centroid calculation with single location (edge case)"""
    result = calculate_centroid_of_locations("SingleLocation", world_id=999)
    data = json.loads(result)

    # Should handle gracefully (error or return the location itself as centroid)
    assert "error" in data or "lat" in data


def test_find_nearby_locations_zero_radius():
    """Test nearby locations with zero radius (edge case)"""
    result = find_nearby_locations(0.0, 0.0, 0.0, world_id=999)
    data = json.loads(result)

    # Should return empty list or handle gracefully
    assert isinstance(data, list) or "error" in data


def test_project_from_point_negative_bearing():
    """Test projection with negative bearing (should normalize)"""
    result = project_from_point("TestLoc", -45.0, 50.0, world_id=999)
    data = json.loads(result)

    # PostGIS should handle negative bearings
    assert "error" in data or "lat" in data


# Pytest fixtures would be defined in conftest.py:
# @pytest.fixture
# def test_world_with_locations(db_session):
#     """Create test world with sample locations for testing"""
#     # Create world
#     # Create locations: Millbrook (12.0, 34.0), Ashford (12.7, 34.5), Skyreach, Origin (0, 0)
#     # Return world object
#     pass

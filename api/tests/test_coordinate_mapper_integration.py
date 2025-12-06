"""End-to-end integration tests for coordinate mapper with DeepAgent (Phase 2)"""

import pytest
from geoalchemy2.elements import WKBElement
from db.models import World, Location
from services.coordinate_mapper import CoordinateMapperService


# NOTE: These tests require:
# 1. Full database setup with PostGIS
# 2. LLM API credentials for DeepAgent
# 3. Test fixtures for world and locations


@pytest.mark.asyncio
async def test_coordinate_mapper_with_deepagent(db_session, test_llm, test_world):
    """Test CoordinateMapperService uses DeepAgent for complex constraints

    This is the main integration test verifying the Phase 2 replacement works
    """
    # Create test locations with coordinates
    millbrook = Location(
        world_id=test_world.id,
        name="Millbrook",
        location_type="village",
        description="A quiet farming community",
        coordinates="SRID=4326;POINT(34.0 12.0)"  # (lon, lat) = (34.0, 12.0)
    )
    ashford = Location(
        world_id=test_world.id,
        name="Ashford",
        location_type="town",
        description="A mining town",
        coordinates="SRID=4326;POINT(34.5 12.7)"  # (lon, lat) = (34.5, 12.7)
    )
    port_town = Location(
        world_id=test_world.id,
        name="Port Town",
        location_type="town",
        description="A coastal trading hub",
        relative_position="between Millbrook and Ashford, near the eastern coast"
    )

    db_session.add_all([millbrook, ashford, port_town])
    db_session.commit()

    # Run coordinate mapper with DeepAgent
    service = CoordinateMapperService(test_llm, db_session)
    await service.assign_coordinates_to_world(test_world.id)

    # Verify Port Town got coordinates
    db_session.refresh(port_town)
    assert port_town.coordinates is not None, "Port Town should have coordinates assigned"

    # Extract lat/lon from WKB geometry
    if isinstance(port_town.coordinates, str):
        # Parse WKT: "SRID=4326;POINT(lon lat)"
        point_part = port_town.coordinates.split('POINT(')[1].rstrip(')')
        lon, lat = map(float, point_part.split())
    else:
        # Handle WKBElement
        from sqlalchemy import text
        result = db_session.execute(
            text("SELECT ST_Y(:geog::geometry) as lat, ST_X(:geog::geometry) as lon"),
            {"geog": str(port_town.coordinates)}
        ).fetchone()
        lat, lon = result.lat, result.lon

    # Verify coordinates are reasonable (should be between Millbrook and Ashford)
    assert 12.0 <= lat <= 12.7, f"Latitude {lat} should be between Millbrook and Ashford"
    assert 34.0 <= lon <= 34.5, f"Longitude {lon} should be between Millbrook and Ashford"


@pytest.mark.asyncio
async def test_twenty_plus_constraint_patterns(db_session, test_llm, test_world):
    """Test 20+ different constraint patterns that the agent must handle

    This is the comprehensive test covering all constraint types from the plan
    """
    # Create reference locations first
    references = [
        Location(world_id=test_world.id, name="Millbrook", location_type="village",
                coordinates="SRID=4326;POINT(34.0 12.0)"),
        Location(world_id=test_world.id, name="Ashford", location_type="town",
                coordinates="SRID=4326;POINT(34.5 12.7)"),
        Location(world_id=test_world.id, name="Skyreach", location_type="city",
                coordinates="SRID=4326;POINT(35.0 13.0)"),
        Location(world_id=test_world.id, name="Capital", location_type="city",
                coordinates="SRID=4326;POINT(33.0 11.0)"),
    ]

    db_session.add_all(references)
    db_session.commit()

    # Define 20+ constraint patterns to test
    test_cases = [
        ("78km northeast of Millbrook", "single reference + precise distance + direction"),
        ("between Millbrook and Ashford", "between two locations"),
        ("halfway between Millbrook and Ashford", "midpoint synonym"),
        ("equidistant from Millbrook, Ashford, and Skyreach", "multiple references"),
        ("far from any settlement", "isolation constraint"),
        ("near the coast", "geographic feature reference"),
        ("2 days travel north of Millbrook", "travel time → distance conversion"),
        ("generally northeast of Ashford, about a day's walk", "fuzzy direction + travel time"),
        ("very close to Capital", "qualitative distance (very close)"),
        ("moderate distance south of Skyreach", "qualitative distance (moderate)"),
        ("very far west of Ashford", "qualitative distance (very far)"),
        ("nearby Millbrook", "qualitative distance (nearby)"),
        ("close to Ashford", "qualitative distance (close)"),
        ("north of Millbrook", "direction only, no distance"),
        ("50km from Capital", "distance only, no direction"),
        ("directly north of Skyreach", "strict bearing qualifier"),
        ("northward from Millbrook", "relaxed bearing qualifier"),
        ("toward Ashford from Millbrook", "bearing toward reference"),
        ("in the mountains near Skyreach", "terrain + proximity"),
        ("on the plains between Millbrook and Capital", "terrain + between"),
        ("across the world from Skyreach", "extreme distance qualifier"),
        ("a week's journey from Capital", "long travel time"),
        ("half day walk from Ashford", "short travel time"),
    ]

    # Create location for each test case
    for relative_position, description in test_cases:
        # Create safe name from description
        safe_name = f"Test_{description.replace(' ', '_').replace('+', 'and')}"[:50]

        location = Location(
            world_id=test_world.id,
            name=safe_name,
            location_type="test_location",
            description=f"Test location for: {description}",
            relative_position=relative_position
        )
        db_session.add(location)

    db_session.commit()

    # Run coordinate mapper (this will invoke DeepAgent for each relative position)
    service = CoordinateMapperService(test_llm, db_session)
    result = await service.assign_coordinates_to_world(test_world.id)

    # Verify all test locations got coordinates
    test_locations = db_session.query(Location).filter(
        Location.world_id == test_world.id,
        Location.name.like('Test_%')
    ).all()

    assert len(test_locations) == len(test_cases), f"Should have {len(test_cases)} test locations"

    failed_locations = []
    for loc in test_locations:
        if loc.coordinates is None:
            failed_locations.append((loc.name, loc.relative_position))

    if failed_locations:
        failure_msg = "\\n".join([f"  - {name}: {pos}" for name, pos in failed_locations])
        pytest.fail(f"Failed to assign coordinates to {len(failed_locations)} locations:\\n{failure_msg}")

    # Verify all coordinates are within quarter-Earth bounds
    for loc in test_locations:
        if loc.coordinates:
            # Extract lat/lon
            if isinstance(loc.coordinates, str):
                point_part = loc.coordinates.split('POINT(')[1].rstrip(')')
                lon, lat = map(float, point_part.split())
            else:
                from sqlalchemy import text
                result = db_session.execute(
                    text("SELECT ST_Y(:geog::geometry) as lat, ST_X(:geog::geometry) as lon"),
                    {"geog": str(loc.coordinates)}
                ).fetchone()
                lat, lon = result.lat, result.lon

            assert -40 <= lat <= 40, \
                f"Location {loc.name} latitude {lat} outside valid range [-40, 40]"
            assert -180 <= lon <= 180, \
                f"Location {loc.name} longitude {lon} outside valid range [-180, 180]"


@pytest.mark.asyncio
async def test_coordinate_mapper_handles_agent_errors_gracefully(db_session, test_llm, test_world):
    """Test that coordinate mapper handles DeepAgent errors without crashing"""
    # Create location with problematic constraint
    location = Location(
        world_id=test_world.id,
        name="ProblematicLocation",
        location_type="test",
        relative_position="this is complete gibberish that cannot be parsed"
    )

    db_session.add(location)
    db_session.commit()

    service = CoordinateMapperService(test_llm, db_session)

    # Should not raise exception, but may log error
    try:
        await service.assign_coordinates_to_world(test_world.id)
    except Exception as e:
        pytest.fail(f"Coordinate mapper should handle errors gracefully, but raised: {e}")

    # Location may or may not have coordinates depending on agent's error handling
    db_session.refresh(location)
    # No assertion - just verify it didn't crash


@pytest.mark.asyncio
async def test_coordinate_mapper_respects_existing_coordinates(db_session, test_llm, test_world):
    """Test that locations with existing coordinates are not overwritten"""
    # Create location with explicit coordinates
    existing_loc = Location(
        world_id=test_world.id,
        name="ExistingLocation",
        location_type="city",
        coordinates="SRID=4326;POINT(35.0 15.0)"
    )

    db_session.add(existing_loc)
    db_session.commit()

    original_coords = existing_loc.coordinates

    service = CoordinateMapperService(test_llm, db_session)
    await service.assign_coordinates_to_world(test_world.id)

    # Verify coordinates unchanged
    db_session.refresh(existing_loc)
    assert existing_loc.coordinates == original_coords, \
        "Existing coordinates should not be overwritten"


@pytest.mark.asyncio
async def test_coordinate_mapper_multi_constraint_validation(db_session, test_llm, test_world):
    """Test that complex multi-constraint scenarios produce reasonable results

    This tests the agent's ability to satisfy multiple constraints simultaneously
    """
    # Create reference locations
    mill = Location(world_id=test_world.id, name="Mill", coordinates="SRID=4326;POINT(30.0 10.0)")
    ash = Location(world_id=test_world.id, name="Ash", coordinates="SRID=4326;POINT(32.0 12.0)")
    sky = Location(world_id=test_world.id, name="Sky", coordinates="SRID=4326;POINT(31.0 14.0)")

    db_session.add_all([mill, ash, sky])

    # Create location with multiple constraints
    complex_loc = Location(
        world_id=test_world.id,
        name="ComplexLocation",
        location_type="village",
        relative_position="between Mill and Ash, close to Sky, near water, 2 days travel from the Capital"
    )

    db_session.add(complex_loc)
    db_session.commit()

    service = CoordinateMapperService(test_llm, db_session)
    await service.assign_coordinates_to_world(test_world.id)

    db_session.refresh(complex_loc)
    assert complex_loc.coordinates is not None, "Complex multi-constraint location should get coordinates"

    # Extract coordinates
    if isinstance(complex_loc.coordinates, str):
        point_part = complex_loc.coordinates.split('POINT(')[1].rstrip(')')
        lon, lat = map(float, point_part.split())

        # Should be somewhere between Mill (10, 30) and Ash (12, 32)
        # Rough sanity check - exact position depends on agent reasoning
        assert 10 <= lat <= 14, "Should be in general area of reference locations"
        assert 30 <= lon <= 32, "Should be in general area of reference locations"


# Pytest fixtures (would be in conftest.py):
# @pytest.fixture
# def test_world(db_session):
#     """Create a test world"""
#     world = World(name="Test World", description="Test world for Phase 2")
#     db_session.add(world)
#     db_session.commit()
#     return world
#
# @pytest.fixture
# def test_llm():
#     """Create test LLM instance"""
#     from config.llm import create_lmstudio_qwen2_5_14b_instruct_llm
#     return create_lmstudio_qwen2_5_14b_instruct_llm()

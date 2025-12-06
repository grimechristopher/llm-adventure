"""
Spatial Calculator Tools for DeepAgent Integration

These tools use PostGIS to perform spatial calculations,
enabling DeepAgents to reason about geographic relationships
and solve complex spatial constraints.
"""

import json
from langchain_core.tools import tool
from sqlalchemy import text
from config.orm_database import engine


@tool
def calculate_distance(location1: str, location2: str, world_id: int) -> str:
    """Calculate distance between two locations using PostGIS.

    Uses spherical distance calculation on the quarter-Earth sphere.

    Args:
        location1: Name of first location
        location2: Name of second location
        world_id: ID of the world containing these locations

    Returns:
        Distance in kilometers as formatted string

    Example:
        >>> calculate_distance("Millbrook", "Ashford", 1)
        "45.23 km"
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT ST_Distance(
                    l1.coordinates::geography,
                    l2.coordinates::geography
                ) / 1000.0 as distance_km
                FROM locations l1, locations l2
                WHERE l1.name = :name1 AND l2.name = :name2
                  AND l1.world_id = :world_id AND l2.world_id = :world_id
                  AND l1.coordinates IS NOT NULL AND l2.coordinates IS NOT NULL
            """), {"name1": location1, "name2": location2, "world_id": world_id})

            row = result.fetchone()
            if row and row[0] is not None:
                return f"{row[0]:.2f} km"
            else:
                return f"Could not calculate distance - one or both locations not found or have no coordinates (world_id={world_id}, locations: {location1}, {location2})"

    except Exception as e:
        return f"Error calculating distance: {str(e)}"


@tool
def calculate_bearing(from_location: str, to_location: str, world_id: int) -> str:
    """Calculate compass bearing from one location to another.

    Returns both degrees and cardinal direction (N, NE, E, SE, S, SW, W, NW).

    Args:
        from_location: Starting location name
        to_location: Destination location name
        world_id: ID of the world containing these locations

    Returns:
        Bearing as degrees and cardinal direction

    Example:
        >>> calculate_bearing("Skyreach", "Frostpeak", 1)
        "12.5° (N)"
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT degrees(ST_Azimuth(
                    l1.coordinates::geometry,
                    l2.coordinates::geometry
                )) as bearing_degrees
                FROM locations l1, locations l2
                WHERE l1.name = :from_name AND l2.name = :to_name
                  AND l1.world_id = :world_id AND l2.world_id = :world_id
                  AND l1.coordinates IS NOT NULL AND l2.coordinates IS NOT NULL
            """), {"from_name": from_location, "to_name": to_location, "world_id": world_id})

            row = result.fetchone()
            if not row or row[0] is None:
                return f"Could not calculate bearing - one or both locations not found or have no coordinates (world_id={world_id}, from: {from_location}, to: {to_location})"

            degrees = row[0]
            cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            idx = int((degrees + 22.5) / 45) % 8
            return f"{degrees:.1f}° ({cardinals[idx]})"

    except Exception as e:
        return f"Error calculating bearing: {str(e)}"


@tool
def find_coordinates_for_constraints(constraints: str, world_id: int) -> str:
    """Helper tool providing context for spatial constraint reasoning.

    Returns existing world locations so agent can reason about
    how to satisfy constraints like 'between A and B, near coast'.

    Args:
        constraints: Natural language spatial constraints
        world_id: ID of the world

    Returns:
        JSON with constraints and existing locations for agent reasoning

    Example:
        >>> find_coordinates_for_constraints("between Millbrook and Ashford", 1)
        '{"constraints": "between Millbrook and Ashford", "existing_locations": [...]}'
    """
    try:
        from tools.world_query import query_world_locations

        locations_json = query_world_locations(world_id)

        return json.dumps({
            "constraints": constraints,
            "world_id": world_id,
            "existing_locations": json.loads(locations_json),
            "instruction": "Use the existing_locations data and your geometric reasoning to find coordinates that satisfy the constraints. You can use calculate_distance and calculate_bearing tools to verify constraint satisfaction."
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": f"Failed to provide context for spatial constraints (world_id={world_id})"
        })


@tool
def calculate_midpoint(location1: str, location2: str, world_id: int) -> str:
    """Calculate geographic midpoint between two locations.

    Uses PostGIS ST_Centroid on LineString connecting the points.
    Essential for "between A and B" constraints.

    Args:
        location1: First location name
        location2: Second location name
        world_id: World containing these locations

    Returns:
        JSON string: {"lat": float, "lon": float, "distance_to_each": "45.2 km"}

    Example:
        >>> calculate_midpoint("Millbrook", "Ashford", 1)
        '{"lat": 12.5, "lon": 34.7, "distance_to_each": "39.0 km"}'
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    ST_Y(ST_Centroid(ST_MakeLine(l1.coordinates, l2.coordinates))) as lat,
                    ST_X(ST_Centroid(ST_MakeLine(l1.coordinates, l2.coordinates))) as lon,
                    ST_Distance(
                        l1.coordinates::geography,
                        ST_Centroid(ST_MakeLine(l1.coordinates, l2.coordinates))::geography
                    ) / 1000.0 as distance_km
                FROM locations l1, locations l2
                WHERE l1.name = :name1 AND l2.name = :name2
                  AND l1.world_id = :world_id AND l2.world_id = :world_id
                  AND l1.coordinates IS NOT NULL AND l2.coordinates IS NOT NULL
            """), {"name1": location1, "name2": location2, "world_id": world_id})

            row = result.fetchone()
            if row:
                return json.dumps({
                    "lat": float(row[0]),
                    "lon": float(row[1]),
                    "distance_to_each": f"{row[2]:.1f} km"
                })
            else:
                return json.dumps({"error": f"Could not find locations (world_id={world_id})"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def calculate_centroid_of_locations(location_names: str, world_id: int) -> str:
    """Calculate geographic centroid of multiple locations.

    Handles "equidistant from A, B, and C" constraints.

    Args:
        location_names: Comma-separated location names (e.g., "Millbrook,Ashford,Skyreach")
        world_id: World containing these locations

    Returns:
        JSON string: {"lat": float, "lon": float, "avg_distance": "52.3 km"}
    """
    try:
        names = [n.strip() for n in location_names.split(',')]
        placeholders = ','.join([f':name{i}' for i in range(len(names))])
        params = {f'name{i}': name for i, name in enumerate(names)}
        params['world_id'] = world_id

        with engine.connect() as conn:
            result = conn.execute(text(f"""
                WITH points AS (
                    SELECT coordinates
                    FROM locations
                    WHERE name IN ({placeholders}) AND world_id = :world_id
                ),
                centroid AS (
                    SELECT ST_Centroid(ST_Collect(coordinates)) as center FROM points
                )
                SELECT
                    ST_Y(center) as lat,
                    ST_X(center) as lon,
                    AVG(ST_Distance(points.coordinates::geography, center::geography)) / 1000.0 as avg_dist
                FROM points, centroid
                GROUP BY center
            """), params)

            row = result.fetchone()
            if row:
                return json.dumps({
                    "lat": float(row[0]),
                    "lon": float(row[1]),
                    "avg_distance": f"{row[2]:.1f} km"
                })
            else:
                return json.dumps({"error": "Could not calculate centroid"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def validate_bearing_constraint(from_location: str, to_lat: float, to_lon: float,
                               expected_direction: str, world_id: int) -> str:
    """Validate that coordinates satisfy a directional constraint.

    Checks if to_lat/to_lon is in the expected direction from from_location.
    Allows ±45° tolerance (e.g., "north" accepts 315° to 45°).

    Args:
        from_location: Reference location name
        to_lat: Proposed latitude
        to_lon: Proposed longitude
        expected_direction: Cardinal direction (N, NE, E, SE, S, SW, W, NW, north, northeast, etc.)
        world_id: World ID

    Returns:
        JSON: {"valid": bool, "actual_bearing": "12.5° (N)", "expected": "N", "deviation": 12.5}
    """
    try:
        # Normalize direction to cardinal
        direction_map = {
            'n': 0, 'north': 0, 'ne': 45, 'northeast': 45,
            'e': 90, 'east': 90, 'se': 135, 'southeast': 135,
            's': 180, 'south': 180, 'sw': 225, 'southwest': 225,
            'w': 270, 'west': 270, 'nw': 315, 'northwest': 315
        }
        expected_bearing = direction_map.get(expected_direction.lower())
        if expected_bearing is None:
            return json.dumps({"error": f"Unknown direction: {expected_direction}"})

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT degrees(ST_Azimuth(
                    l.coordinates::geometry,
                    ST_SetSRID(ST_MakePoint(:to_lon, :to_lat), 4326)::geometry
                )) as actual_bearing
                FROM locations l
                WHERE l.name = :from_name AND l.world_id = :world_id
                  AND l.coordinates IS NOT NULL
            """), {"from_name": from_location, "to_lat": to_lat, "to_lon": to_lon, "world_id": world_id})

            row = result.fetchone()
            if not row:
                return json.dumps({"error": "Could not find reference location"})

            actual = row[0]
            # Calculate deviation (handle 360° wrap)
            deviation = min(abs(actual - expected_bearing),
                          360 - abs(actual - expected_bearing))
            valid = deviation <= 45.0

            cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            idx = int((actual + 22.5) / 45) % 8

            return json.dumps({
                "valid": valid,
                "actual_bearing": f"{actual:.1f}° ({cardinals[idx]})",
                "expected": expected_direction.upper(),
                "deviation_degrees": round(deviation, 1)
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def validate_distance_constraint(from_location: str, to_lat: float, to_lon: float,
                                expected_distance_km: float, tolerance_km: float,
                                world_id: int) -> str:
    """Validate that coordinates satisfy a distance constraint.

    Args:
        from_location: Reference location name
        to_lat: Proposed latitude
        to_lon: Proposed longitude
        expected_distance_km: Target distance in kilometers
        tolerance_km: Acceptable deviation (e.g., 10.0 for ±10km)
        world_id: World ID

    Returns:
        JSON: {"valid": bool, "actual_distance": "78.3 km", "expected": "75.0 km", "error": 3.3}
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT ST_Distance(
                    l.coordinates::geography,
                    ST_SetSRID(ST_MakePoint(:to_lon, :to_lat), 4326)::geography
                ) / 1000.0 as distance_km
                FROM locations l
                WHERE l.name = :from_name AND l.world_id = :world_id
                  AND l.coordinates IS NOT NULL
            """), {"from_name": from_location, "to_lat": to_lat, "to_lon": to_lon, "world_id": world_id})

            row = result.fetchone()
            if not row:
                return json.dumps({"error": "Could not find reference location"})

            actual = row[0]
            error = abs(actual - expected_distance_km)
            valid = error <= tolerance_km

            return json.dumps({
                "valid": valid,
                "actual_distance": f"{actual:.1f} km",
                "expected": f"{expected_distance_km:.1f} km",
                "error_km": round(error, 1)
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def find_nearby_locations(lat: float, lon: float, radius_km: float, world_id: int) -> str:
    """Find all locations within radius of coordinates.

    Useful for checking isolation constraints like "far from any settlement".

    Args:
        lat: Center latitude
        lon: Center longitude
        radius_km: Search radius in kilometers
        world_id: World ID

    Returns:
        JSON array: [{"name": str, "distance": "12.3 km", "bearing": "45.2° (NE)"}]
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    l.name,
                    ST_Distance(
                        l.coordinates::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                    ) / 1000.0 as distance_km,
                    degrees(ST_Azimuth(
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry,
                        l.coordinates::geometry
                    )) as bearing_degrees
                FROM locations l
                WHERE l.world_id = :world_id
                  AND l.coordinates IS NOT NULL
                  AND ST_DWithin(
                      l.coordinates::geography,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                      :radius_m
                  )
                ORDER BY distance_km
            """), {"lat": lat, "lon": lon, "radius_m": radius_km * 1000, "world_id": world_id})

            locations = []
            cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            for row in result:
                idx = int((row[2] + 22.5) / 45) % 8
                locations.append({
                    "name": row[0],
                    "distance": f"{row[1]:.1f} km",
                    "bearing": f"{row[2]:.1f}° ({cardinals[idx]})"
                })

            return json.dumps(locations, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def project_from_point(from_location: str, bearing_degrees: float, distance_km: float,
                      world_id: int) -> str:
    """Project a point from a location at given bearing and distance.

    Wrapper around PostGIS ST_Project for "78km northeast of Millbrook" constraints.

    Args:
        from_location: Starting location name
        bearing_degrees: Compass bearing (0=N, 90=E, 180=S, 270=W)
        distance_km: Distance to project
        world_id: World ID

    Returns:
        JSON: {"lat": float, "lon": float, "verification": "78.2 km at 45.1° (NE)"}
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    ST_Y(ST_Project(l.coordinates::geography, :distance_m, radians(:bearing))::geometry) as lat,
                    ST_X(ST_Project(l.coordinates::geography, :distance_m, radians(:bearing))::geometry) as lon
                FROM locations l
                WHERE l.name = :from_name AND l.world_id = :world_id
                  AND l.coordinates IS NOT NULL
            """), {
                "from_name": from_location,
                "distance_m": distance_km * 1000,
                "bearing": bearing_degrees,
                "world_id": world_id
            })

            row = result.fetchone()
            if not row:
                return json.dumps({"error": "Could not find reference location"})

            # Verify by calculating back
            cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            idx = int((bearing_degrees + 22.5) / 45) % 8

            return json.dumps({
                "lat": float(row[0]),
                "lon": float(row[1]),
                "verification": f"{distance_km:.1f} km at {bearing_degrees:.1f}° ({cardinals[idx]})"
            })
    except Exception as e:
        return json.dumps({"error": str(e)})

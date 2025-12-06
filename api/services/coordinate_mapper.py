"""
Coordinate Mapper Service - PostGIS Spatial Intelligence

This service maps natural language relative positions ("far north of Capital") to actual
PostGIS coordinates on a quarter-Earth sphere (constrained to -40° to +40° lat/lon).

Key Features:
- LLM-powered parsing of relative position text
- PostGIS ST_Project for accurate spherical projections
- Anchor location distribution using Fibonacci sphere algorithm
- Conflict detection and resolution for overlapping locations
- Support for complex constraints (between X and Y, near coast, etc.)

Architecture:
- Uses geoalchemy2 for PostGIS Geography type handling
- Integrates with world_builder agents for relative position parsing
- Follows quarter-Earth constraint (-40° to +40° bounds)
"""

import math
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, ST_Project, ST_MakePoint, ST_X, ST_Y
from db.models import Location
from agents.world_builder import create_relative_position_parser_chain
from models.world_building import RelativePositionParse, CoordinateAssignmentSummary
from utils.logging import get_logger

logger = get_logger(__name__)

# NOTE: Hardcoded dictionaries removed in Phase 2 - DeepAgent integration
# Previous DISTANCE_QUALIFIERS and DIRECTION_BEARINGS replaced with
# spatial_planner_agent.py which uses extended reasoning instead of lookups


class CoordinateMapperService:
    """
    Service for assigning PostGIS coordinates to locations based on relative positions.
    """

    def __init__(self, llm, db_session: Session):
        """
        Initialize coordinate mapper.

        Args:
            llm: Language model for parsing relative positions
            db_session: SQLAlchemy database session
        """
        self.llm = llm
        self.db = db_session
        self.parser_chain, _ = create_relative_position_parser_chain(llm)
        logger.info("CoordinateMapperService initialized")

    async def assign_coordinates_to_world(self, world_id: int) -> CoordinateAssignmentSummary:
        """
        Assign coordinates to all locations in a world.

        Multi-phase process:
        1. Identify anchor locations (no relative_position)
        2. Distribute anchors across sphere using Fibonacci algorithm
        3. Resolve relative positions using PostGIS projections
        4. Detect and resolve coordinate conflicts

        Args:
            world_id: ID of the world to process

        Returns:
            CoordinateAssignmentSummary with assignment statistics
        """
        logger.info("Starting coordinate assignment", world_id=world_id)

        # Get all locations for this world
        locations = self.db.query(Location).filter_by(world_id=world_id).all()

        if not locations:
            logger.warning("No locations found for world", world_id=world_id)
            return CoordinateAssignmentSummary(
                total_locations=0,
                locations_with_coordinates=0,
                anchor_locations=0,
                relative_locations=0
            )

        # Phase 1: Identify anchors
        anchors = self._identify_anchor_locations(locations)
        relatives = [loc for loc in locations if loc not in anchors]

        logger.info("Identified location types",
                    anchors=len(anchors),
                    relatives=len(relatives))

        # Phase 2: Distribute anchors
        self._distribute_anchor_locations(anchors)

        # Phase 3: Resolve relative positions
        await self._resolve_relative_positions(relatives, locations)

        # Phase 4: Conflict resolution
        self._resolve_conflicts(locations)

        # Commit coordinates
        self.db.commit()

        # Calculate summary
        locations_with_coords = sum(1 for loc in locations if loc.coordinates is not None)

        logger.info("Coordinate assignment complete",
                    world_id=world_id,
                    total_locations=len(locations),
                    assigned=locations_with_coords)

        return CoordinateAssignmentSummary(
            total_locations=len(locations),
            locations_with_coordinates=locations_with_coords,
            anchor_locations=len(anchors),
            relative_locations=len(relatives)
        )

    def _identify_anchor_locations(self, locations: List[Location]) -> List[Location]:
        """
        Identify anchor locations (those without relative positions).

        If no anchors exist, select the "most important" location as primary anchor.

        Args:
            locations: List of all locations

        Returns:
            List of anchor locations
        """
        anchors = [loc for loc in locations if not loc.relative_position or not loc.relative_position.strip()]

        if not anchors:
            # No explicit anchors - choose the first location as primary anchor
            logger.info("No anchor locations found, using first location as primary anchor")
            anchors = [locations[0]]

        return anchors

    def _distribute_anchor_locations(self, anchors: List[Location]) -> None:
        """
        Distribute anchor locations across the sphere using Fibonacci sphere algorithm.

        This ensures even spacing of anchor points on the quarter-Earth sphere.

        Args:
            anchors: List of anchor locations to distribute
        """
        if not anchors:
            return

        logger.info("Distributing anchor locations", count=len(anchors))

        for i, anchor in enumerate(anchors):
            if i == 0:
                # First anchor at origin (0, 0)
                lat, lon = 0.0, 0.0
            else:
                # Use Fibonacci sphere for even distribution
                lat, lon = self._fibonacci_sphere_point(i, len(anchors))

            # Set coordinates using PostGIS Geography type
            # We need to create a WKT POINT string for geoalchemy2
            anchor.coordinates = f'SRID=4326;POINT({lon} {lat})'

            logger.debug("Anchor location positioned",
                         name=anchor.name,
                         latitude=lat,
                         longitude=lon)

    def _fibonacci_sphere_point(self, index: int, total_points: int) -> Tuple[float, float]:
        """
        Calculate evenly distributed point on sphere using Fibonacci spiral.

        Constrained to -40° to +40° for quarter-Earth.

        Args:
            index: Point index
            total_points: Total number of points to distribute

        Returns:
            Tuple of (latitude, longitude) in degrees
        """
        phi = math.pi * (3.0 - math.sqrt(5.0))  # Golden angle

        y = 1 - (index / float(total_points - 1)) * 2  # y from 1 to -1
        radius = math.sqrt(1 - y * y)

        theta = phi * index

        x = math.cos(theta) * radius
        z = math.sin(theta) * radius

        # Convert to lat/lon constrained to -40 to +40
        longitude = (math.atan2(z, x) * 180 / math.pi) * (40 / 180)
        latitude = (math.asin(y) * 180 / math.pi) * (40 / 90)

        # Ensure bounds
        latitude = max(-40, min(40, latitude))
        longitude = max(-40, min(40, longitude))

        return latitude, longitude

    async def _resolve_relative_positions(self, relatives: List[Location], all_locations: List[Location]) -> None:
        """
        Resolve relative positions using LLM parsing and PostGIS projections.

        Args:
            relatives: Locations with relative positions
            all_locations: All locations (for reference lookup)
        """
        if not relatives:
            return

        logger.info("Resolving relative positions", count=len(relatives))

        for loc in relatives:
            try:
                # Parse relative position using LLM
                parsed = await self.parser_chain.ainvoke({
                    "relative_position": loc.relative_position
                })

                # Calculate coordinates using DeepAgent (Phase 2)
                coords = await self._calculate_coordinates_from_parse(loc, parsed, all_locations)

                if coords:
                    lat, lon = coords
                    loc.coordinates = f'SRID=4326;POINT({lon} {lat})'
                    logger.debug("Relative location positioned",
                                 name=loc.name,
                                 relative_to=parsed.reference_location_name,
                                 latitude=lat,
                                 longitude=lon)
                else:
                    logger.warning("Could not calculate coordinates for location",
                                   name=loc.name,
                                   relative_position=loc.relative_position)

            except Exception as e:
                logger.error("Failed to resolve relative position",
                             name=loc.name,
                             relative_position=loc.relative_position,
                             error=str(e))

    async def _calculate_coordinates_from_parse(
        self,
        location: Location,
        parsed: RelativePositionParse,
        all_locations: List[Location]
    ) -> Optional[Tuple[float, float]]:
        """
        Calculate coordinates using DeepAgent spatial reasoning.

        CLEAN REPLACEMENT - No fallback to old dictionary logic.
        Phase 2: Uses spatial_planner_agent instead of hardcoded dictionaries.

        Args:
            location: Location object with relative_position text
            parsed: Parsed relative position data (may be used for fallback in future)
            all_locations: All locations for reference lookup

        Returns:
            Tuple of (latitude, longitude) or None if calculation fails
        """
        from agents.spatial_planner_agent import create_spatial_planner_agent
        import json

        # Create agent
        agent = create_spatial_planner_agent()

        # Invoke agent with full relative_position context
        result = agent.invoke({
            "messages": [{
                "role": "user",
                "content": f"""Find coordinates for location '{location.name}'.

**Constraint Description**: {location.relative_position}

**World ID**: {location.world_id}

**Instructions**:
1. Use query_world_locations to see existing locations
2. Parse all constraints from the description
3. Use calculation tools to propose coordinates
4. Use validation tools to verify all constraints
5. Return JSON with proposed_lat, proposed_lon, and validation results
"""
            }]
        })

        # Parse agent's response
        final_message = result['messages'][-1]['content']

        # Extract JSON from agent response
        try:
            # Agent should return JSON, but might wrap it in markdown
            if '```json' in final_message:
                json_str = final_message.split('```json')[1].split('```')[0].strip()
            elif '```' in final_message:
                json_str = final_message.split('```')[1].split('```')[0].strip()
            else:
                json_str = final_message.strip()

            agent_output = json.loads(json_str)

            lat = float(agent_output['proposed_lat'])
            lon = float(agent_output['proposed_lon'])

            # Validate coordinates are in bounds
            if not (-40 <= lat <= 40):
                raise ValueError(f"Latitude {lat} outside valid range [-40, 40]")
            if not (-180 <= lon <= 180):
                raise ValueError(f"Longitude {lon} outside valid range [-180, 180]")

            # Log agent reasoning for debugging
            logger.info(
                "Spatial planner agent result",
                location=location.name,
                coordinates={"lat": lat, "lon": lon},
                confidence=agent_output.get('confidence', 'unknown'),
                constraints_satisfied=[
                    v['constraint'] for v in agent_output.get('validation_results', [])
                    if v.get('satisfied', False)
                ]
            )

            return lat, lon

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "Failed to parse spatial planner output",
                error=str(e),
                agent_output=final_message[:500]
            )
            raise ValueError(f"Spatial planner agent did not return valid coordinates: {e}")

    def _extract_lat_lon_from_geography(self, geography) -> Tuple[float, float]:
        """
        Extract latitude and longitude from PostGIS Geography object.

        Args:
            geography: PostGIS Geography object or WKT string

        Returns:
            Tuple of (latitude, longitude)
        """
        if isinstance(geography, str):
            # Parse WKT string: "SRID=4326;POINT(lon lat)"
            point_part = geography.split('POINT(')[1].rstrip(')')
            lon, lat = map(float, point_part.split())
            return lat, lon

        # Handle geoalchemy2 Geography object
        result = self.db.execute(
            text("""
                SELECT ST_Y(:geog::geometry) as lat, ST_X(:geog::geometry) as lon
            """),
            {"geog": str(geography)}
        ).fetchone()

        return result.lat, result.lon

    def _resolve_conflicts(self, locations: List[Location], min_distance_km: float = 5.0) -> None:
        """
        Detect and resolve locations that are too close together.

        Args:
            locations: All locations to check
            min_distance_km: Minimum allowed distance in kilometers
        """
        logger.info("Checking for coordinate conflicts", min_distance_km=min_distance_km)

        conflicts_resolved = 0

        for i, loc1 in enumerate(locations):
            if not loc1.coordinates:
                continue

            for loc2 in locations[i + 1:]:
                if not loc2.coordinates:
                    continue

                # Calculate distance using PostGIS
                distance_m = self.db.execute(
                    text("""
                        SELECT ST_Distance(:geog1::geography, :geog2::geography) as dist
                    """),
                    {"geog1": str(loc1.coordinates), "geog2": str(loc2.coordinates)}
                ).scalar()

                distance_km = distance_m / 1000

                if distance_km < min_distance_km:
                    logger.warning("Conflict detected",
                                   loc1=loc1.name,
                                   loc2=loc2.name,
                                   distance_km=distance_km)

                    # Adjust loc2 by adding random offset
                    self._adjust_location_with_offset(loc2, offset_km=10)
                    conflicts_resolved += 1

        if conflicts_resolved > 0:
            logger.info("Conflicts resolved", count=conflicts_resolved)

    def _adjust_location_with_offset(self, location: Location, offset_km: float) -> None:
        """
        Adjust location coordinates with a small random offset.

        Args:
            location: Location to adjust
            offset_km: Offset distance in kilometers
        """
        import random

        # Random direction
        bearing = random.uniform(0, 360)
        azimuth_radians = math.radians(bearing)
        distance_meters = offset_km * 1000

        # Project from current coordinates
        result = self.db.execute(
            text("""
                SELECT
                    ST_Y(ST_Project(:geog::geography, :dist, :azimuth)::geometry) as lat,
                    ST_X(ST_Project(:geog::geography, :dist, :azimuth)::geometry) as lon
            """),
            {
                "geog": str(location.coordinates),
                "dist": distance_meters,
                "azimuth": azimuth_radians
            }
        ).fetchone()

        if result:
            lat, lon = result.lat, result.lon

            # Enforce bounds
            lat = max(-40, min(40, lat))
            lon = max(-40, min(40, lon))

            location.coordinates = f'SRID=4326;POINT({lon} {lat})'

            logger.debug("Location adjusted",
                         name=location.name,
                         offset_km=offset_km,
                         new_lat=lat,
                         new_lon=lon)

"""
Service layer for world-building operations
Handles business logic for world creation and LLM-driven fact extraction
"""
from sqlalchemy.orm import Session
from db.models import World, Location, Fact
from models.world_building import WorldCreate, WorldBuildingExtraction
from agents.world_builder import create_world_builder_chain
from utils.logging import get_logger

logger = get_logger(__name__)


class WorldBuildingService:
    """Service for managing world-building operations"""

    def __init__(self, db_session: Session, llm):
        """
        Initialize the world-building service

        Args:
            db_session: SQLAlchemy database session
            llm: Language model for extraction
        """
        self.db = db_session
        self.llm = llm
        self.chain, self.parser = create_world_builder_chain(llm)

    async def create_world(self, world_data: WorldCreate) -> World:
        """
        Create a new world

        Args:
            world_data: World creation data

        Returns:
            Created World instance
        """
        world = World(**world_data.dict())
        self.db.add(world)
        self.db.commit()
        self.db.refresh(world)
        logger.info("Created new world", world_id=world.id, world_name=world.name)
        return world

    async def extract_and_save(self, world_id: int, description: str):
        """
        Extract locations and facts from natural language description and save to database

        Args:
            world_id: ID of the world to add content to
            description: Natural language world description

        Returns:
            dict with created locations and facts

        Raises:
            ValueError: If world_id doesn't exist
        """

        # 1. Verify world exists
        world = self.db.query(World).filter(World.id == world_id).first()
        if not world:
            raise ValueError(f"World {world_id} not found")

        # 2. LLM extraction
        logger.info("Extracting world data from description", world_id=world_id, description_length=len(description))
        try:
            extracted = await self.chain.ainvoke({
                "description": description,
                "format_instructions": self.parser.get_format_instructions()
            })
        except Exception as e:
            logger.error("LLM extraction failed", error=str(e), world_id=world_id)
            raise

        # 3. Save locations
        location_map = {}  # name -> Location object
        for loc_data in extracted.locations:
            location = Location(
                world_id=world_id,
                **loc_data.dict()
            )
            self.db.add(location)
            self.db.flush()  # Get ID without committing
            location_map[location.name.lower()] = location
            logger.info("Created location", location_id=location.id, name=location.name, world_id=world_id)

        # 4. Save facts (resolve location references)
        facts_created = []
        for fact_data in extracted.facts:
            # Resolve location_name to location_id
            location_id = None
            if fact_data.location_name:
                loc = location_map.get(fact_data.location_name.lower())
                if loc:
                    location_id = loc.id
                else:
                    # Try to find existing location in this world
                    existing_loc = self.db.query(Location).filter(
                        Location.world_id == world_id,
                        Location.name.ilike(fact_data.location_name)
                    ).first()
                    if existing_loc:
                        location_id = existing_loc.id

            fact = Fact(
                world_id=world_id,
                content=fact_data.content,
                fact_category=fact_data.fact_category,
                what_type=fact_data.what_type,
                location_id=location_id
            )
            self.db.add(fact)
            facts_created.append(fact)
            logger.info(
                "Created fact",
                fact_category=fact.fact_category,
                content=fact.content[:50] + "..." if len(fact.content) > 50 else fact.content,
                world_id=world_id,
                location_id=location_id
            )

        # 5. Commit all changes
        self.db.commit()

        logger.info(
            "World-building extraction complete",
            world_id=world_id,
            locations_created=len(location_map),
            facts_created=len(facts_created)
        )

        return {
            "locations": list(location_map.values()),
            "facts": facts_created
        }

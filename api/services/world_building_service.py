"""
Service layer for world-building operations
Handles business logic for world creation and LLM-driven fact extraction
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from db.models import World, Location, Fact, WorldGenerationSession
from models.world_building import (
    WorldCreate,
    WorldBuildingExtraction,
    WizardStartResponse,
    WizardResponseResponse,
    WizardFinalizeResponse,
    CoordinateAssignmentSummary
)
from agents.world_builder import (
    create_world_builder_chain,
    create_wizard_question_chain,
    create_wizard_completion_evaluator_chain
)
from services.coordinate_mapper import CoordinateMapperService
from services.checklist_evaluator import ChecklistEvaluator
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


class WizardOrchestrationService:
    """
    Service for managing adaptive multi-question world-building wizard.

    This service orchestrates the conversational world-building flow:
    1. Asks questions based on current stage and gathered data
    2. Extracts structured information from user responses
    3. Determines when enough information has been collected
    4. Finalizes world creation with coordinate assignment
    """

    # Question stages in order
    STAGES = ['world_identity', 'locations', 'complete']

    # First question for each stage
    STAGE_QUESTIONS = {
        'world_identity': "Let's start building your world! What kind of world do you want to create? Tell me about the genre, tone, and core concept.",
        'locations': "Great! Now tell me about the key locations in your world. Describe 3-5 important places with their spatial relationships (e.g., 'north of', 'far from', 'between').",
    }

    def __init__(self, db_session: Session, llm):
        """
        Initialize wizard orchestration service.

        Args:
            db_session: SQLAlchemy database session
            llm: Language model for wizard agents
        """
        self.db = db_session
        self.llm = llm
        self.extraction_chain, _ = create_world_builder_chain(llm)
        self.question_chain, _ = create_wizard_question_chain(llm)
        self.completion_chain, _ = create_wizard_completion_evaluator_chain(llm)
        self.checklist_evaluator = ChecklistEvaluator()
        logger.info("WizardOrchestrationService initialized")

    async def start_session(self, world_id: int) -> WizardStartResponse:
        """
        Start a new wizard session for a world.

        Args:
            world_id: ID of the world being created

        Returns:
            WizardStartResponse with session ID and first question

        Raises:
            ValueError: If world doesn't exist
        """
        # Verify world exists
        world = self.db.query(World).filter_by(id=world_id).first()
        if not world:
            raise ValueError(f"World {world_id} not found")

        # Create session
        session = WorldGenerationSession(
            world_id=world_id,
            session_stage='world_identity',
            current_question_type='world_identity',
            conversation_history=[],
            gathered_data={}
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info("Started wizard session", session_id=session.id, world_id=world_id)

        # Return first question
        first_question = self.STAGE_QUESTIONS['world_identity']

        # Add to conversation history
        session.conversation_history.append({
            "role": "assistant",
            "content": first_question,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.db.commit()

        return WizardStartResponse(
            session_id=session.id,
            first_question=first_question,
            stage='world_identity'
        )

    async def respond(self, session_id: int, user_response: str) -> WizardResponseResponse:
        """
        Process user response and determine next action.

        Args:
            session_id: ID of the wizard session
            user_response: User's answer to the current question

        Returns:
            WizardResponseResponse with next question or completion status

        Raises:
            ValueError: If session doesn't exist or is already complete
        """
        # Get session
        session = self.db.query(WorldGenerationSession).filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.is_complete:
            raise ValueError(f"Session {session_id} is already complete")

        logger.info("Processing wizard response", session_id=session_id, stage=session.session_stage)

        # Add user response to conversation history
        session.conversation_history.append({
            "role": "user",
            "content": user_response,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Extract data from response
        try:
            extracted = await self.extraction_chain.ainvoke({
                "description": user_response
            })

            # Merge extracted data into gathered_data
            if 'locations' not in session.gathered_data:
                session.gathered_data['locations'] = []
            if 'facts' not in session.gathered_data:
                session.gathered_data['facts'] = []

            session.gathered_data['locations'].extend([loc.dict() for loc in extracted.locations])
            session.gathered_data['facts'].extend([fact.dict() for fact in extracted.facts])

            logger.info("Extracted data from response",
                        locations=len(extracted.locations),
                        facts=len(extracted.facts))

        except Exception as e:
            logger.error("Failed to extract data from response", error=str(e))
            # Continue anyway - extraction is best-effort

        # CHECKLIST EVALUATION: Check requirements after each response
        checklist_result = self.checklist_evaluator.evaluate_gathered_data(session.gathered_data)

        logger.info("Checklist evaluation after user response",
                    overall_complete=checklist_result['overall_complete'],
                    percentage=checklist_result['overall_percentage'],
                    satisfied=len(checklist_result['satisfied_requirements']),
                    missing=len(checklist_result['missing_requirements']))

        # Store checklist result in session metadata for debugging
        if 'checklist_evaluations' not in session.gathered_data:
            session.gathered_data['checklist_evaluations'] = []
        session.gathered_data['checklist_evaluations'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'result': checklist_result
        })

        # Evaluate if current stage is complete
        is_stage_complete = await self._is_stage_complete(session)

        if is_stage_complete:
            # Advance to next stage
            next_stage = self._advance_stage(session)

            if next_stage == 'complete':
                # All stages complete
                session.is_complete = True
                session.completed_at = datetime.utcnow()
                self.db.commit()

                logger.info("Wizard session complete", session_id=session_id)

                return WizardResponseResponse(
                    next_question=None,
                    is_complete=True,
                    current_stage='complete',
                    gathered_so_far=session.gathered_data,
                    progress_percentage=100
                )

            # Ask first question of next stage
            next_question = self.STAGE_QUESTIONS[next_stage]
        else:
            # Continue current stage - ask follow-up question
            next_question = await self._generate_follow_up_question(session)

        # Add question to conversation history
        session.conversation_history.append({
            "role": "assistant",
            "content": next_question,
            "timestamp": datetime.utcnow().isoformat()
        })

        self.db.commit()

        # Calculate progress
        progress = self._calculate_progress(session)

        return WizardResponseResponse(
            next_question=next_question,
            is_complete=False,
            current_stage=session.session_stage,
            gathered_so_far=session.gathered_data,
            progress_percentage=progress
        )

    async def finalize(self, session_id: int) -> WizardFinalizeResponse:
        """
        Finalize world generation from wizard session.

        Creates all locations and facts, assigns coordinates using PostGIS.

        Args:
            session_id: ID of the wizard session

        Returns:
            WizardFinalizeResponse with creation summary

        Raises:
            ValueError: If session doesn't exist or isn't complete
        """
        # Get session
        session = self.db.query(WorldGenerationSession).filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.is_complete:
            raise ValueError(f"Session {session_id} is not complete yet")

        logger.info("Finalizing wizard session", session_id=session_id, world_id=session.world_id)

        # Create locations
        location_map = {}
        for loc_data in session.gathered_data.get('locations', []):
            location = Location(
                world_id=session.world_id,
                name=loc_data['name'],
                description=loc_data.get('description'),
                location_type=loc_data.get('location_type'),
                relative_position=loc_data.get('relative_position'),
                elevation_meters=loc_data.get('elevation_meters')
            )
            self.db.add(location)
            self.db.flush()
            location_map[location.name.lower()] = location

        logger.info("Created locations from wizard", count=len(location_map))

        # Create facts
        facts_created = []
        myths_created = 0

        for fact_data in session.gathered_data.get('facts', []):
            # Resolve location reference
            location_id = None
            if fact_data.get('location_name'):
                loc = location_map.get(fact_data['location_name'].lower())
                if loc:
                    location_id = loc.id

            fact = Fact(
                world_id=session.world_id,
                content=fact_data['content'],
                fact_category=fact_data['fact_category'],
                what_type=fact_data.get('what_type'),
                location_id=location_id,
                canonical_truth=fact_data.get('canonical_truth', True)
            )
            self.db.add(fact)
            facts_created.append(fact)

            if not fact.canonical_truth:
                myths_created += 1

        logger.info("Created facts from wizard",
                    total=len(facts_created),
                    myths=myths_created)

        self.db.commit()

        # Assign coordinates using CoordinateMapperService
        coord_mapper = CoordinateMapperService(self.llm, self.db)
        coord_summary = await coord_mapper.assign_coordinates_to_world(session.world_id)

        logger.info("Wizard finalization complete",
                    session_id=session_id,
                    world_id=session.world_id,
                    locations=len(location_map),
                    facts=len(facts_created))

        return WizardFinalizeResponse(
            world_id=session.world_id,
            locations_created=len(location_map),
            facts_created=len(facts_created) - myths_created,
            myths_created=myths_created,
            coordinate_assignment=coord_summary
        )

    async def _is_stage_complete(self, session: WorldGenerationSession) -> bool:
        """
        Determine if current stage has enough information using checklist evaluation.

        Uses the configurable checklist to verify all required information has been
        gathered with sufficient detail. This handles vague responses by checking
        both quantity and quality of gathered data.

        Args:
            session: Current wizard session

        Returns:
            True if stage is complete (all checklist items satisfied)
        """
        # Get latest checklist evaluation (already computed after user response)
        checklist_evals = session.gathered_data.get('checklist_evaluations', [])
        if not checklist_evals:
            # No evaluation yet - shouldn't happen but fallback to false
            logger.warning("No checklist evaluation found, defaulting to incomplete")
            return False

        latest_eval = checklist_evals[-1]['result']

        # Check if overall checklist is complete
        overall_complete = latest_eval['overall_complete']

        logger.info("Checklist-based stage completion",
                    stage=session.session_stage,
                    overall_complete=overall_complete,
                    percentage=latest_eval['overall_percentage'],
                    satisfied=len(latest_eval['satisfied_requirements']),
                    missing=len(latest_eval['missing_requirements']))

        # If checklist says incomplete, use LLM as secondary check for quality
        if not overall_complete:
            return False

        # Checklist complete - use LLM to verify quality
        try:
            evaluation = await self.completion_chain.ainvoke({
                "gathered_data": str(session.gathered_data)
            })

            logger.info("LLM quality verification",
                        is_complete=evaluation.is_complete,
                        missing_elements=evaluation.missing_elements)

            return evaluation.is_complete

        except Exception as e:
            logger.error("Failed LLM quality verification, trusting checklist", error=str(e))
            # Trust checklist if LLM fails
            return overall_complete

    def _advance_stage(self, session: WorldGenerationSession) -> str:
        """
        Advance session to next stage.

        Args:
            session: Current wizard session

        Returns:
            Name of next stage
        """
        current_index = self.STAGES.index(session.session_stage)
        next_index = current_index + 1

        if next_index >= len(self.STAGES):
            return 'complete'

        next_stage = self.STAGES[next_index]
        session.session_stage = next_stage
        session.current_question_type = next_stage

        logger.info("Advanced wizard stage",
                    session_id=session.id,
                    from_stage=self.STAGES[current_index],
                    to_stage=next_stage)

        return next_stage

    async def _generate_follow_up_question(self, session: WorldGenerationSession) -> str:
        """
        Generate an intelligent follow-up question using checklist + LLM.

        The checklist identifies what's missing, and the LLM crafts a natural
        question to gather that information.

        Args:
            session: Current wizard session

        Returns:
            Follow-up question text
        """
        # Get latest checklist evaluation
        checklist_evals = session.gathered_data.get('checklist_evaluations', [])
        if checklist_evals:
            latest_eval = checklist_evals[-1]['result']
            next_priority = latest_eval.get('next_priority', '')
            missing_reqs = latest_eval.get('missing_requirements', [])

            logger.info("Generating follow-up based on checklist",
                        next_priority=next_priority,
                        missing_count=len(missing_reqs))
        else:
            next_priority = "Ask about world details"
            missing_reqs = []

        # Use LLM to generate natural follow-up incorporating checklist guidance
        try:
            # Build context for LLM
            context_parts = [
                f"Next priority from checklist: {next_priority}",
                f"Missing requirements: {[r['name'] for r in missing_reqs[:3]]}"  # Top 3
            ]

            if missing_reqs:
                # Include example from first missing requirement
                first_missing = missing_reqs[0]
                context_parts.append(f"Example of good answer: {first_missing.get('example_good', '')}")

            gathered_data_str = str(session.gathered_data)
            context_str = " | ".join(context_parts)

            result = await self.question_chain.ainvoke({
                "stage": session.session_stage,
                "questions_asked": len([m for m in session.conversation_history if m.get('role') == 'assistant']),
                "gathered_data": f"{gathered_data_str}\n\nCHECKLIST GUIDANCE: {context_str}"
            })

            return result.question_text

        except Exception as e:
            logger.error("Failed to generate intelligent follow-up, using checklist hint", error=str(e))

            # Fallback to direct checklist hint
            if next_priority and next_priority != "All requirements satisfied":
                return next_priority

            # Final fallback to generic prompts
            if session.session_stage == 'world_identity':
                return "Tell me more about your world. What makes it unique? What are the key themes or conflicts?"
            elif session.session_stage == 'locations':
                return "Any other important locations? Or tell me more about the places you've mentioned."
            return "Is there anything else you'd like to add?"

    def _calculate_progress(self, session: WorldGenerationSession) -> int:
        """
        Calculate wizard progress percentage.

        Args:
            session: Current wizard session

        Returns:
            Progress percentage (0-100)
        """
        if session.is_complete:
            return 100

        stage_index = self.STAGES.index(session.session_stage)
        total_stages = len(self.STAGES) - 1  # Exclude 'complete'

        base_progress = int((stage_index / total_stages) * 100)

        # Add partial progress within stage based on data gathered
        if session.session_stage == 'world_identity':
            facts = len(session.gathered_data.get('facts', []))
            partial = min(20, facts * 10)  # Up to 20% for facts
        elif session.session_stage == 'locations':
            locations = len(session.gathered_data.get('locations', []))
            partial = min(20, locations * 5)  # Up to 20% for locations
        else:
            partial = 0

        return min(100, base_progress + partial)

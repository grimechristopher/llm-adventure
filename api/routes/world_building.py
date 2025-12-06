"""
World-building API routes
"""
from quart import Blueprint, request, jsonify, current_app
from pydantic import ValidationError
from models.world_building import (
    WorldCreate,
    WorldBuildingRequest,
    WorldBuildingResponse,
    WizardStartRequest,
    WizardResponseRequest,
    WizardFinalizeRequest
)
from services.world_building_service import WorldBuildingService, WizardOrchestrationService
from config.orm_database import get_db_session
from db.models import Location, Fact
from utils.logging import get_logger

logger = get_logger(__name__)
world_building_routes = Blueprint('world_building', __name__, url_prefix='/world-building')


@world_building_routes.route('/worlds', methods=['POST'])
async def create_world():
    """
    Create a new world

    Request body:
        {
            "name": "World Name",
            "description": "Optional description",
            "created_by_user": "Optional user identifier"
        }

    Returns:
        201: World created successfully
        400: Validation error
        500: Internal server error
    """
    try:
        data = await request.get_json()
        world_data = WorldCreate(**data)

        db = next(get_db_session())
        llm = current_app.llms.get('azure_one')
        service = WorldBuildingService(db, llm)

        world = await service.create_world(world_data)

        return jsonify({
            "id": world.id,
            "name": world.name,
            "description": world.description,
            "created_by_user": world.created_by_user
        }), 201

    except ValidationError as e:
        logger.warning("Validation error creating world", error=e.errors())
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except Exception as e:
        logger.error("Failed to create world", error=str(e))
        return jsonify({"error": "Internal server error"}), 500


@world_building_routes.route('/describe', methods=['POST'])
async def describe_world():
    """
    Extract and save world information from natural language description

    Request body:
        {
            "world_id": 1,
            "description": "Natural language world description..."
        }

    Returns:
        200: Extraction successful
        400: Validation error
        404: World not found
        500: Internal server error
    """
    try:
        data = await request.get_json()
        req = WorldBuildingRequest(**data)

        db = next(get_db_session())
        llm = current_app.llms.get('azure_one')
        service = WorldBuildingService(db, llm)

        result = await service.extract_and_save(req.world_id, req.description)

        response = WorldBuildingResponse(
            world_id=req.world_id,
            locations_created=len(result['locations']),
            facts_created=len(result['facts']),
            locations=[{
                "id": loc.id,
                "name": loc.name,
                "description": loc.description,
                "location_type": loc.location_type,
                "relative_position": loc.relative_position,
                "elevation_meters": loc.elevation_meters
            } for loc in result['locations']],
            facts=[{
                "id": fact.id,
                "content": fact.content,
                "fact_category": fact.fact_category,
                "what_type": fact.what_type,
                "location_id": fact.location_id
            } for fact in result['facts']]
        )

        return jsonify(response.dict()), 200

    except ValidationError as e:
        logger.warning("Validation error describing world", error=e.errors())
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except ValueError as e:
        logger.warning("World not found", error=str(e))
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error("Failed to process world description", error=str(e))
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@world_building_routes.route('/worlds/<int:world_id>/locations', methods=['GET'])
async def get_locations(world_id: int):
    """
    Get all locations for a world

    Returns:
        200: List of locations
        500: Internal server error
    """
    try:
        db = next(get_db_session())
        locations = db.query(Location).filter(Location.world_id == world_id).all()

        return jsonify({
            "world_id": world_id,
            "count": len(locations),
            "locations": [{
                "id": loc.id,
                "name": loc.name,
                "description": loc.description,
                "location_type": loc.location_type,
                "relative_position": loc.relative_position,
                "elevation_meters": loc.elevation_meters
            } for loc in locations]
        }), 200

    except Exception as e:
        logger.error("Failed to get locations", error=str(e), world_id=world_id)
        return jsonify({"error": "Internal server error"}), 500


@world_building_routes.route('/worlds/<int:world_id>/facts', methods=['GET'])
async def get_facts(world_id: int):
    """
    Get all facts for a world

    Returns:
        200: List of facts
        500: Internal server error
    """
    try:
        db = next(get_db_session())
        facts = db.query(Fact).filter(Fact.world_id == world_id).all()

        return jsonify({
            "world_id": world_id,
            "count": len(facts),
            "facts": [{
                "id": fact.id,
                "content": fact.content,
                "fact_category": fact.fact_category,
                "what_type": fact.what_type,
                "location_id": fact.location_id
            } for fact in facts]
        }), 200

    except Exception as e:
        logger.error("Failed to get facts", error=str(e), world_id=world_id)
        return jsonify({"error": "Internal server error"}), 500


# ========== WIZARD ENDPOINTS ==========

@world_building_routes.route('/wizard/start', methods=['POST'])
async def wizard_start():
    """
    Start a wizard session for world building

    Request body:
        {
            "world_id": 1
        }

    Returns:
        200: Session started with first question
        400: Validation error
        404: World not found
        500: Internal server error
    """
    try:
        data = await request.get_json()
        req = WizardStartRequest(**data)

        db = next(get_db_session())
        llm = current_app.llms.get('azure_one')
        service = WizardOrchestrationService(db, llm)

        response = await service.start_session(req.world_id)

        return jsonify(response.dict()), 200

    except ValidationError as e:
        logger.warning("Validation error starting wizard", error=e.errors())
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except ValueError as e:
        logger.warning("World not found for wizard", error=str(e))
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error("Failed to start wizard", error=str(e))
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@world_building_routes.route('/wizard/respond', methods=['POST'])
async def wizard_respond():
    """
    Respond to a wizard question

    Request body:
        {
            "session_id": 1,
            "response": "User's answer to the question..."
        }

    Returns:
        200: Next question or completion status
        400: Validation error
        404: Session not found
        500: Internal server error
    """
    try:
        data = await request.get_json()
        req = WizardResponseRequest(**data)

        db = next(get_db_session())
        llm = current_app.llms.get('azure_one')
        service = WizardOrchestrationService(db, llm)

        response = await service.respond(req.session_id, req.response)

        return jsonify(response.dict()), 200

    except ValidationError as e:
        logger.warning("Validation error responding to wizard", error=e.errors())
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except ValueError as e:
        logger.warning("Wizard session error", error=str(e))
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error("Failed to process wizard response", error=str(e))
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@world_building_routes.route('/wizard/finalize', methods=['POST'])
async def wizard_finalize():
    """
    Finalize world creation from wizard session

    Creates all locations and facts, assigns PostGIS coordinates

    Request body:
        {
            "session_id": 1
        }

    Returns:
        200: World finalized successfully
        400: Validation error or session not complete
        404: Session not found
        500: Internal server error
    """
    try:
        data = await request.get_json()
        req = WizardFinalizeRequest(**data)

        db = next(get_db_session())
        llm = current_app.llms.get('azure_one')
        service = WizardOrchestrationService(db, llm)

        response = await service.finalize(req.session_id)

        return jsonify(response.dict()), 200

    except ValidationError as e:
        logger.warning("Validation error finalizing wizard", error=e.errors())
        return jsonify({"error": "Validation error", "details": e.errors()}), 400
    except ValueError as e:
        logger.warning("Wizard finalization error", error=str(e))
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Failed to finalize wizard", error=str(e))
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

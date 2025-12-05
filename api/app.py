"""
LLM Adventure API Application

A Quart-based API for an LLM-powered adventure game.
"""

import os
from quart import Quart, jsonify
from dotenv import load_dotenv

from config.llm import initialize_llms
from config.orm_database import test_postgres_connection, initialize_database
from routes.general import general_routes
from routes.world_building import world_building_routes
from routes.errors import register_error_handlers
from utils.logging import setup_logging, get_logger

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = get_logger(__name__)

def create_app():
    """Create and configure the app"""
    logger.info("Creating Quart application")

    app = Quart(__name__, static_folder=None)

    # Simple configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.getenv('DEBUG', 'True').lower() == 'true'
    app.config['PROVIDE_AUTOMATIC_OPTIONS'] = True

    logger.info("Initializing LLMs")
    # Initialize LLMs
    app.llms = initialize_llms()

    logger.info("Registering routes")
    # Register routes
    app.register_blueprint(general_routes)
    app.register_blueprint(world_building_routes)

    # Register error handlers
    register_error_handlers(app)

    # Register startup event to initialize database
    @app.before_serving
    async def startup():
        """Initialize database connection on startup"""
        logger.info("Starting database initialization")
        db_connected = test_postgres_connection()
        db_initialized = await initialize_database()

        if db_connected:
            logger.info("Database connection successful - PostgreSQL is ready")
        else:
            logger.error("Database connection failed")

        if db_initialized:
            logger.info("Database initialized successfully - PostgreSQL is ready")
        else:
            logger.error("Database initialization failed - chat history will not work")

    logger.info("Application created successfully")
    return app
"""
LLM Adventure API Application

A Quart-based API for an LLM-powered adventure game.
"""

import os
from quart import Quart, jsonify
from dotenv import load_dotenv

from config.llm import initialize_llms
from routes.general import general_routes
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
    
    app = Quart(__name__)
    
    # Simple configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.getenv('DEBUG', 'True').lower() == 'true'
    app.config['PROVIDE_AUTOMATIC_OPTIONS'] = True  # Required for Quart
    
    logger.info("Initializing LLMs")
    # Initialize LLMs
    app.llms = initialize_llms()
    
    logger.info("Registering routes")
    # Register routes
    app.register_blueprint(general_routes)
    
    # Register error handlers
    register_error_handlers(app)
    
    logger.info("Application created successfully")
    return app
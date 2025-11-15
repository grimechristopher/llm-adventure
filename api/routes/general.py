"""
General routes for LLM Adventure API

Basic endpoints for health checks and welcome messages.
"""

from quart import Blueprint, jsonify
from utils.logging import get_logger

logger = get_logger(__name__)

# Create general routes blueprint
general_routes = Blueprint('general', __name__)

@general_routes.route('/')
async def welcome():
    """Welcome message endpoint"""
    logger.info("Welcome endpoint accessed")
    return jsonify({
        'message': 'Welcome to LLM Adventure API!',
        'status': 'running',
        'description': 'An AI-powered adventure game API'
    })

@general_routes.route('/health')
async def health_check():
    """Health check endpoint"""
    logger.info("Health check endpoint accessed")
    return jsonify({
        'status': 'healthy',
        'service': 'llm-adventure-api',
        'version': '1.0.0'
    })
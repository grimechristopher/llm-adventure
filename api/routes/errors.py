"""
Error handlers for LLM Adventure API

HTTP error handlers that return JSON responses.
"""

from quart import jsonify

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    async def not_found_error(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found.'
        }), 404
    
    @app.errorhandler(500)
    async def internal_server_error(error):
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred.'
        }), 500
    
    @app.errorhandler(400)
    async def bad_request_error(error):
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request was invalid or malformed.'
        }), 400
import os
from quart import Quart, render_template, request, jsonify, session
from dotenv import load_dotenv
import secrets
from adventure_game import AdventureGame

# Load environment variables
load_dotenv()

app = Quart(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Initialize the adventure game
adventure_game = AdventureGame()

@app.route('/health')
async def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'LLM Adventure API is running'})

@app.errorhandler(404)
async def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
async def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
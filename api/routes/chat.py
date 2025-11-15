"""
Simple chat route
"""

from quart import Blueprint, jsonify, request, current_app
from agents.simple_agent import chat

chat_routes = Blueprint('chat', __name__, url_prefix='/chat')


@chat_routes.route('/', methods=['POST'])
async def chat_endpoint():
    """Chat with LM Studio"""
    data = await request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    llm = current_app.llms.get('lm_studio')
    if not llm:
        return jsonify({'error': 'LLM not available'}), 503
    
    try:
        response = await chat(llm, message)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
from flask import Blueprint, jsonify, request
import logging
from utils.session import get_session_id
from utils.validation import validate_request_data
from utils.database import db_transaction, create_and_save
from models.core import db, Conversation, Message
from services.api_client import OpenRouterClient
from services.memory_aware_chat_service import get_memory_aware_chat_service

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
logger = logging.getLogger(__name__)
client = OpenRouterClient()
chat_service = get_memory_aware_chat_service()

@chat_bp.route('/send', methods=['POST'])
@validate_request_data(required_fields=['message'])
def send_message(validated_data):
    """Send a message and get AI response with memory optimization"""
    session_id = get_session_id()

    try:
        message = validated_data.get('message', '').strip()
        model = validated_data.get('model', 'openai/gpt-4')
        conversation_id = validated_data.get('conversation_id')
        chat_type = validated_data.get('chat_type', 'v2')
            
        # Create or get chat with memory-aware service
        if not conversation_id:
            conversation_id = chat_service.create_chat(
                user_id=session_id, 
                chat_type=chat_type,
                metadata={'model': model}
            )
        
        # Add user message
        chat_service.add_message(conversation_id, 'user', message)
        
        # Get chat history from memory-aware service
        messages = chat_service.get_chat_history(conversation_id, limit=50)
        
        # Add current message if not already in history
        if not messages or messages[-1]['content'] != message:
            messages.append({"role": "user", "content": message})
        
        # Get AI response
        response = client.call_api(messages, model)
        
        if response and 'choices' in response:
            ai_content = response['choices'][0]['message']['content']

            # Save AI response
            chat_service.add_message(conversation_id, 'assistant', ai_content)
            
            # Also save to database for compatibility
            with db_transaction():
                conversation = Conversation.query.filter_by(
                    id=conversation_id,
                    session_id=session_id
                ).first()
                
                if not conversation:
                    conversation = Conversation(
                        id=conversation_id,
                        session_id=session_id,
                        model_id=model,
                        title=message[:50] + '...' if len(message) > 50 else message
                    )
                    db.session.add(conversation)
                
                # Save messages
                user_msg = Message(
                    conversation_id=conversation.id,
                    message_id=f"msg_{conversation.id}_{len(conversation.messages) + 1}",
                    role="user",
                    content=message,
                    model_used=model
                )
                db.session.add(user_msg)
                
                ai_msg = Message(
                    conversation_id=conversation.id,
                    message_id=f"msg_{conversation.id}_{len(conversation.messages) + 2}",
                    role="assistant",
                    content=ai_content,
                    model_used=model
                )
                db.session.add(ai_msg)
            
            return jsonify({
                'success': True,
                'message': ai_content,
                'conversation_id': conversation_id,
                'model': model
            })
        else:
            return jsonify({'error': 'Failed to get AI response'}), 500
            
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for the current session"""
    session_id = get_session_id()
    
    try:
        conversations = Conversation.query.filter_by(
            session_id=session_id,
            is_active=True
        ).order_by(Conversation.updated_at.desc()).all()
        
        return jsonify({
            'conversations': [conv.to_dict() for conv in conversations],
            'total': len(conversations)
        })
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/history/<conversation_id>', methods=['GET'])
def get_chat_history(conversation_id):
    """Get chat history from memory-aware service"""
    try:
        limit = request.args.get('limit', 100, type=int)
        history = chat_service.get_chat_history(conversation_id, limit)
        
        return jsonify({
            'success': True,
            'messages': history,
            'count': len(history)
        })
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/search', methods=['POST'])
@validate_request_data(required_fields=['query'])
def search_chats(validated_data):
    """Search through chat history"""
    session_id = get_session_id()
    
    try:
        query = validated_data.get('query')
        chat_type = validated_data.get('chat_type')
        
        results = chat_service.search_chats(session_id, query, chat_type)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        logger.error(f"Error searching chats: {e}")
        return jsonify({'error': str(e)}), 500
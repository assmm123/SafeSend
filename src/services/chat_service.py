"""
Chat Service - WebSocket - SafeSend
خدمة المحادثة - WebSocket - SafeSend

Handles real-time messaging via WebSocket using Flask-SocketIO.
يدير المراسلة الفورية عبر WebSocket باستخدام Flask-SocketIO.
"""

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from datetime import datetime, timezone
from typing import Optional
import structlog

from src.app.models.database import get_db
from src.app.models.message import Message, MessageType
from src.app.models.conversation import Conversation

logger = structlog.get_logger(__name__)

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*")

# Track online users: {user_id: sid}
online_users = {}

# Track typing status
typing_users = {}


def init_socketio(app):
    """Initialize SocketIO with Flask app."""
    socketio.init_app(app)
    logger.info("socketio.initialized")
    return socketio


# ============================================
# Connection Events
# ============================================

@socketio.on('connect')
def handle_connect():
    """User connected."""
    user_id = request.args.get('user_id')
    if user_id:
        online_users[user_id] = request.sid
        logger.info("socketio.user_connected", user_id=user_id)
        emit('user_status', {'user_id': user_id, 'status': 'online'}, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    """User disconnected."""
    for uid, sid in list(online_users.items()):
        if sid == request.sid:
            del online_users[uid]
            logger.info("socketio.user_disconnected", user_id=uid)
            emit('user_status', {'user_id': uid, 'status': 'offline'}, broadcast=True)
            break


# ============================================
# Messaging Events
# ============================================

@socketio.on('send_message')
def handle_send_message(data):
    """
    Handle sending a message via WebSocket.
    معالجة إرسال رسالة عبر WebSocket.
    """
    user_id = data.get('user_id')
    conversation_id = data.get('conversation_id')
    content = data.get('content', '')
    message_type = data.get('type', 'text')
    reply_to = data.get('reply_to')
    
    if not user_id or not conversation_id or not content:
        emit('error', {'message': 'Missing required fields'})
        return
    
    try:
        db = next(get_db())
        
        # Create message in database
        msg = Message(
            conversation_id=conversation_id,
            sender_id=str(user_id),
            content=content,
            content_type=message_type if message_type in ['text', 'image', 'video', 'file', 'audio'] else MessageType.TEXT,
            is_read=False
        )
        db.add(msg)
        
        # Update conversation
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            conv.last_message_at = datetime.now(timezone.utc)
            conv.last_message_preview = content[:100]
        
        db.commit()
        db.refresh(msg)
        
        message_data = {
            'id': msg.id,
            'sender_id': str(user_id),
            'conversation_id': conversation_id,
            'content': content,
            'type': message_type,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        db.close()
        
        # Emit to conversation room
        emit('new_message', message_data, room=conversation_id)
        logger.info("socketio.message_sent", msg_id=msg.id, conversation_id=conversation_id)
        
    except Exception as e:
        logger.error("socketio.send_failed", error=str(e))
        emit('error', {'message': 'Failed to send message'})


@socketio.on('join_conversation')
def handle_join_conversation(data):
    """Join a conversation room."""
    conversation_id = data.get('conversation_id')
    if conversation_id:
        join_room(conversation_id)
        logger.info("socketio.joined_room", room=conversation_id)


@socketio.on('leave_conversation')
def handle_leave_conversation(data):
    """Leave a conversation room."""
    conversation_id = data.get('conversation_id')
    if conversation_id:
        leave_room(conversation_id)


@socketio.on('typing')
def handle_typing(data):
    """Typing indicator."""
    user_id = data.get('user_id')
    conversation_id = data.get('conversation_id')
    is_typing = data.get('is_typing', True)
    
    if user_id and conversation_id:
        emit('user_typing', {
            'user_id': user_id,
            'is_typing': is_typing
        }, room=conversation_id, include_self=False)


@socketio.on('mark_read')
def handle_mark_read(data):
    """Mark messages as read."""
    user_id = data.get('user_id')
    conversation_id = data.get('conversation_id')
    message_ids = data.get('message_ids', [])
    
    if not conversation_id:
        return
    
    try:
        db = next(get_db())
        query = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != str(user_id),
            Message.is_read == False
        )
        if message_ids:
            query = query.filter(Message.id.in_(message_ids))
        
        unread = query.all()
        for msg in unread:
            msg.mark_as_read()
        
        count = len(unread)
        db.commit()
        db.close()
        
        emit('messages_read', {
            'conversation_id': conversation_id,
            'count': count,
            'message_ids': [m.id for m in unread]
        }, room=conversation_id)
        
    except Exception as e:
        logger.error("socketio.mark_read_failed", error=str(e))


__all__ = [
    'socketio',
    'online_users',
    'init_socketio',
    'handle_connect',
    'handle_disconnect',
    'handle_send_message',
    'handle_join_conversation',
    'handle_leave_conversation',
    'handle_typing',
    'handle_mark_read'
]

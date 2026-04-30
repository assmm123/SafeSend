"""
Messages API Endpoints - SafeSend
نقاط نهاية الرسائل - SafeSend

Handles conversations, messaging, typing indicators, and read receipts.
يدير المحادثات، المراسلة، مؤشرات الكتابة، وإيصالات القراءة.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import structlog

from src.app.models.database import get_db
from src.app.models.message import Message, MessageType
from src.app.models.conversation import Conversation, ConversationStatus
from src.app.models.user import User
from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token
from src.api.schemas import MessageSchema, ConversationSchema

logger = structlog.get_logger(__name__)
messages_bp = Blueprint('messages_v1', __name__, url_prefix='/api/v1/messages')

# ============================================================
# 🔐 Helpers
# ============================================================

def _get_user_id() -> Optional[int]:
    """Extract user_id from JWT token."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None
    payload = decode_token(token)
    if payload and 'user_id' in payload:
        try:
            return payload['user_id']
        except Exception:
            return None
    return None

def _require_auth():
    """Check authentication and return user_id or error."""
    user_id = _get_user_id()
    if not user_id:
        return None, (jsonify({
            'error': 'Authentication required',
            'message_ar': 'المصادقة مطلوبة'
        }), 401)
    return user_id, None

# Typing status (in-memory - for WebSocket later)
_typing_status = {}

# ============================================================
# 💬 Conversations
# ============================================================

@messages_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """List user conversations from database. / قائمة محادثات المستخدم."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        user_id_str = str(user_id)
        
        conversations = db.query(Conversation).filter(
            (Conversation.buyer_id == user_id_str) | (Conversation.seller_id == user_id_str)
        ).order_by(Conversation.last_message_at.desc()).all()
        
        result = []
        for conv in conversations:
            # Get other user info
            other_id = conv.seller_id if conv.buyer_id == user_id_str else conv.buyer_id
            other_user = db.query(User).filter(User.id == int(other_id)).first() if other_id.isdigit() else None
            
            # Get unread count
            unread = db.query(Message).filter(
                Message.conversation_id == conv.id,
                Message.sender_id != user_id_str,
                Message.is_read == False
            ).count()
            
            result.append({
                'id': conv.id,
                'deal_id': conv.deal_id,
                'name': other_user.username if other_user else 'مستخدم',
                'avatar': other_user.avatar_url if other_user else None,
                'lastMsg': conv.last_message_preview or '',
                'time': conv.last_message_at.isoformat() if conv.last_message_at else None,
                'unread': unread,
                'online': False,  # From WebSocket later
                'starred': False,
                'deal': conv.deal_id or ''
            })
        
        db.close()
        return jsonify({'conversations': result}), 200
        
    except Exception as e:
        logger.error("conversation.list_failed", error=str(e))
        return jsonify({'error': 'Failed to list conversations', 'message_ar': 'فشل جلب المحادثات'}), 500


@messages_bp.route('/<conversation_id>', methods=['GET'])
def get_messages(conversation_id: str):
    """Get conversation messages from database. / رسائل المحادثة."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        before_id = request.args.get('before_id', None, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        db = next(get_db())
        
        query = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc())
        
        if before_id:
            query = query.filter(Message.id < before_id)
        
        messages = query.limit(limit).all()
        messages.reverse()  # oldest first
        
        # Mark as read
        for msg in messages:
            if str(msg.sender_id) != str(user_id) and not msg.is_read:
                msg.mark_as_read()
        
        db.commit()
        
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'content': msg.content,
                'message_type': msg.content_type,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat() if msg.created_at else None
            })
        
        db.close()
        
        return jsonify({
            'messages': result,
            'has_more': len(messages) == limit
        }), 200
        
    except Exception as e:
        logger.error("messages.get_failed", error=str(e))
        return jsonify({'error': 'Failed to fetch messages', 'message_ar': 'فشل جلب الرسائل'}), 500


@messages_bp.route('', methods=['POST'])
def send_message():
    """Send a message to database. / إرسال رسالة."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        conversation_id = data.get('conversation_id', '')
        content = data.get('content', '')
        message_type = data.get('type', 'text')
        reply_to = data.get('reply_to')
        
        if not conversation_id or not content:
            return jsonify({
                'error': 'Conversation ID and content required',
                'message_ar': 'معرف المحادثة والمحتوى مطلوبان'
            }), 400
        
        db = next(get_db())
        
        # Create message
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
        
        msg_id = msg.id
        db.close()
        
        logger.info("message.sent", msg_id=msg_id, conversation_id=conversation_id)
        
        return jsonify({
            'message': 'Message sent',
            'message_ar': 'تم إرسال الرسالة',
            'data': {
                'id': msg_id,
                'sender_id': str(user_id),
                'content': content,
                'message_type': message_type,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error("message.send_failed", error=str(e))
        return jsonify({'error': 'Failed to send message', 'message_ar': 'فشل إرسال الرسالة'}), 500


@messages_bp.route('/<conversation_id>/messages/<int:message_id>', methods=['PUT'])
def edit_message(conversation_id: str, message_id: int):
    """Edit a message in database. / تعديل رسالة."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        new_content = data.get('content', '')
        
        if not new_content:
            return jsonify({'error': 'Content required', 'message_ar': 'المحتوى مطلوب'}), 400
        
        db = next(get_db())
        msg = db.query(Message).filter(
            Message.id == message_id,
            Message.conversation_id == conversation_id
        ).first()
        
        if not msg:
            db.close()
            return jsonify({'error': 'Message not found', 'message_ar': 'الرسالة غير موجودة'}), 404
        
        if str(msg.sender_id) != str(user_id):
            db.close()
            return jsonify({'error': 'Can only edit own messages', 'message_ar': 'يمكن تعديل رسائلك فقط'}), 403
        
        msg.edit(new_content)
        db.commit()
        db.close()
        
        return jsonify({
            'message': 'Message edited',
            'message_ar': 'تم تعديل الرسالة',
            'data': {'id': msg.id, 'content': msg.content, 'edited_at': msg.edited_at.isoformat() if msg.edited_at else None}
        }), 200
        
    except Exception as e:
        logger.error("message.edit_failed", error=str(e))
        return jsonify({'error': 'Edit failed', 'message_ar': 'فشل التعديل'}), 500


@messages_bp.route('/<conversation_id>/messages/<int:message_id>', methods=['DELETE'])
def delete_message(conversation_id: str, message_id: int):
    """Soft delete a message in database. / حذف رسالة."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        msg = db.query(Message).filter(
            Message.id == message_id,
            Message.conversation_id == conversation_id
        ).first()
        
        if not msg:
            db.close()
            return jsonify({'error': 'Message not found', 'message_ar': 'الرسالة غير موجودة'}), 404
        
        if str(msg.sender_id) != str(user_id):
            db.close()
            return jsonify({'error': 'Can only delete own messages', 'message_ar': 'يمكن حذف رسائلك فقط'}), 403
        
        msg.delete()
        db.commit()
        db.close()
        
        return jsonify({'message': 'Message deleted', 'message_ar': 'تم حذف الرسالة'}), 200
        
    except Exception as e:
        logger.error("message.delete_failed", error=str(e))
        return jsonify({'error': 'Delete failed', 'message_ar': 'فشل الحذف'}), 500


@messages_bp.route('/<conversation_id>/read', methods=['POST'])
def mark_as_read(conversation_id: str):
    """Mark messages as read in database. / تعليم الرسائل كمقروءة."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        message_ids = data.get('message_ids', [])
        
        db = next(get_db())
        
        query = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != str(user_id),
            Message.is_read == False
        )
        
        if message_ids:
            query = query.filter(Message.id.in_(message_ids))
        
        unread_messages = query.all()
        marked_count = 0
        
        for msg in unread_messages:
            msg.mark_as_read()
            marked_count += 1
        
        db.commit()
        db.close()
        
        return jsonify({
            'message': f'{marked_count} messages marked as read',
            'message_ar': f'تم تعليم {marked_count} رسالة كمقروءة',
            'marked_count': marked_count
        }), 200
        
    except Exception as e:
        logger.error("messages.read_failed", error=str(e))
        return jsonify({'error': 'Failed to mark as read', 'message_ar': 'فشل تعليم القراءة'}), 500


@messages_bp.route('/unread/count', methods=['GET'])
def unread_count():
    """Get unread count from database. / عدد غير المقروء."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        user_id_str = str(user_id)
        
        # Get user's conversations
        conv_ids = db.query(Conversation.id).filter(
            (Conversation.buyer_id == user_id_str) | (Conversation.seller_id == user_id_str)
        ).all()
        conv_id_list = [c[0] for c in conv_ids]
        
        if not conv_id_list:
            db.close()
            return jsonify({'total_unread': 0}), 200
        
        total_unread = db.query(Message).filter(
            Message.conversation_id.in_(conv_id_list),
            Message.sender_id != user_id_str,
            Message.is_read == False
        ).count()
        
        db.close()
        return jsonify({'total_unread': total_unread}), 200
        
    except Exception as e:
        logger.error("messages.unread_failed", error=str(e))
        return jsonify({'total_unread': 0}), 200


@messages_bp.route('/typing/<conversation_id>', methods=['POST'])
def typing_indicator(conversation_id: str):
    """Typing indicator (in-memory). / مؤشر كتابة."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        data = request.get_json(silent=True) or {}
        is_typing = data.get('is_typing', True)
        
        _typing_status[conversation_id] = {
            'user_id': user_id,
            'is_typing': is_typing,
            'updated_at': datetime.now(timezone.utc)
        }
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error("typing.failed", error=str(e))
        return jsonify({'error': 'Failed to update typing status', 'message_ar': 'فشل تحديث حالة الكتابة'}), 500


__all__ = ['messages_bp']

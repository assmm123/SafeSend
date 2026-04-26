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

from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token
from src.api.schemas import (
    validate_request,
    MessageCreateSchema,
    MessageSchema,
    ConversationSchema
)

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
            return int(payload['user_id'])
        except (ValueError, TypeError):
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

def _get_deal_repo():
    """Get deal repository instance."""
    return DealRepository()

# Temporary in-memory message store
_messages = {}
_conversations = {}
_message_counter = 0
_typing_status = {}

# ============================================================
# 💬 Conversations
# ============================================================

@messages_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """List user conversations. / قائمة محادثات المستخدم."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        user_conversations = [
            conv for conv in _conversations.values()
            if conv['seller_id'] == user_id or conv['buyer_id'] == user_id
        ]
        
        return jsonify({
            'conversations': ConversationSchema().dump(user_conversations, many=True)
        }), 200
        
    except Exception as e:
        logger.error("conversation.list_failed", error=str(e))
        return jsonify({'error': 'Failed to list conversations', 'message_ar': 'فشل جلب المحادثات'}), 500


@messages_bp.route('/conversations/<uuid:deal_uuid>', methods=['GET'])
def get_messages(deal_uuid: str):
    """Get conversation messages. / رسائل المحادثة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        before_id = request.args.get('before_id', None, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        deal_messages = _messages.get(str(deal_uuid), [])
        
        if before_id:
            deal_messages = [m for m in deal_messages if m['id'] < before_id]
        
        deal_messages = deal_messages[-limit:]
        
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'messages': MessageSchema().dump(deal_messages, many=True),
            'has_more': len(deal_messages) == limit
        }), 200
        
    except Exception as e:
        logger.error("messages.get_failed", error=str(e))
        return jsonify({'error': 'Failed to fetch messages', 'message_ar': 'فشل جلب الرسائل'}), 500


@messages_bp.route('/conversations/<uuid:deal_uuid>', methods=['POST'])
@validate_request(MessageCreateSchema())
def send_message(deal_uuid: str, validated_data: dict):
    """Send a message. / إرسال رسالة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            conv_id = str(deal_uuid)
            if conv_id not in _conversations:
                _conversations[conv_id] = {
                    'id': 1, 'deal_id': 1, 'seller_id': user_id,
                    'buyer_id': 0, 'last_message_at': None,
                    'last_message_preview': None, 'is_active': True
                }
        
        global _message_counter
        _message_counter += 1
        msg_id = _message_counter
        
        message = {
            'id': msg_id, 'conversation_id': 1, 'sender_id': user_id,
            'content': validated_data['content'],
            'message_type': validated_data.get('message_type', 'text'),
            'reply_to_id': validated_data.get('reply_to_id'),
            'is_read': False, 'attachments': [],
            'created_at': datetime.now(timezone.utc)
        }
        
        if str(deal_uuid) not in _messages:
            _messages[str(deal_uuid)] = []
        _messages[str(deal_uuid)].append(message)
        
        conv = _conversations.get(str(deal_uuid))
        if conv:
            conv['last_message_at'] = message['created_at']
            conv['last_message_preview'] = validated_data['content'][:100]
        
        logger.info("message.sent", msg_id=msg_id)
        
        return jsonify({
            'message': 'Message sent', 'message_ar': 'تم إرسال الرسالة',
            'data': MessageSchema().dump(message)
        }), 201
        
    except Exception as e:
        logger.error("message.send_failed", error=str(e))
        return jsonify({'error': 'Failed to send message', 'message_ar': 'فشل إرسال الرسالة'}), 500


@messages_bp.route('/conversations/<uuid:deal_uuid>/messages/<int:message_id>', methods=['PUT'])
def edit_message(deal_uuid: str, message_id: int):
    """Edit a message. / تعديل رسالة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        new_content = data.get('content', '')
        
        if not new_content:
            return jsonify({'error': 'Content required', 'message_ar': 'المحتوى مطلوب'}), 400
        
        deal_messages = _messages.get(str(deal_uuid), [])
        for msg in deal_messages:
            if msg['id'] == message_id:
                if msg['sender_id'] != user_id:
                    return jsonify({'error': 'Can only edit own messages', 'message_ar': 'يمكن تعديل رسائلك فقط'}), 403
                
                msg['content'] = new_content
                msg['edited_at'] = datetime.now(timezone.utc)
                
                return jsonify({
                    'message': 'Message edited', 'message_ar': 'تم تعديل الرسالة',
                    'data': MessageSchema().dump(msg)
                }), 200
        
        return jsonify({'error': 'Message not found', 'message_ar': 'الرسالة غير موجودة'}), 404
        
    except Exception as e:
        logger.error("message.edit_failed", error=str(e))
        return jsonify({'error': 'Edit failed', 'message_ar': 'فشل التعديل'}), 500


@messages_bp.route('/conversations/<uuid:deal_uuid>/messages/<int:message_id>', methods=['DELETE'])
def delete_message(deal_uuid: str, message_id: int):
    """Delete a message. / حذف رسالة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        deal_messages = _messages.get(str(deal_uuid), [])
        for msg in deal_messages:
            if msg['id'] == message_id:
                if msg['sender_id'] != user_id:
                    return jsonify({'error': 'Can only delete own messages', 'message_ar': 'يمكن حذف رسائلك فقط'}), 403
                
                msg['is_deleted'] = True
                msg['deleted_at'] = datetime.now(timezone.utc)
                
                return jsonify({'message': 'Message deleted', 'message_ar': 'تم حذف الرسالة'}), 200
        
        return jsonify({'error': 'Message not found', 'message_ar': 'الرسالة غير موجودة'}), 404
        
    except Exception as e:
        logger.error("message.delete_failed", error=str(e))
        return jsonify({'error': 'Delete failed', 'message_ar': 'فشل الحذف'}), 500


@messages_bp.route('/conversations/<uuid:deal_uuid>/read', methods=['POST'])
def mark_as_read(deal_uuid: str):
    """Mark messages as read. / تعليم الرسائل كمقروءة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        message_ids = data.get('message_ids', [])
        
        deal_messages = _messages.get(str(deal_uuid), [])
        marked_count = 0
        
        for msg in deal_messages:
            if not message_ids or msg['id'] in message_ids:
                if not msg['is_read']:
                    msg['is_read'] = True
                    msg['read_at'] = datetime.now(timezone.utc)
                    marked_count += 1
        
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
    """Get unread count. / عدد غير المقروء."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        total_unread = sum(
            sum(1 for m in msgs if not m.get('is_read'))
            for msgs in _messages.values()
        )
        
        return jsonify({'total_unread': total_unread}), 200
        
    except Exception as e:
        return jsonify({'total_unread': 0}), 200


@messages_bp.route('/typing/<uuid:deal_uuid>', methods=['POST'])
def typing_indicator(deal_uuid: str):
    """Typing indicator. / مؤشر كتابة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        is_typing = data.get('is_typing', True)
        
        _typing_status[str(deal_uuid)] = {
            'user_id': user_id, 'is_typing': is_typing,
            'updated_at': datetime.now(timezone.utc)
        }
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error("typing.failed", error=str(e))
        return jsonify({'error': 'Failed to update typing status', 'message_ar': 'فشل تحديث حالة الكتابة'}), 500


@messages_bp.route('/conversations/<uuid:deal_uuid>/export', methods=['GET'])
def export_conversation(deal_uuid: str):
    """Export conversation. / تصدير المحادثة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        deal_messages = _messages.get(str(deal_uuid), [])
        
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'message_count': len(deal_messages),
            'messages': deal_messages
        }), 200
        
    except Exception as e:
        logger.error("conversation.export_failed", error=str(e))
        return jsonify({'error': 'Export failed', 'message_ar': 'فشل التصدير'}), 500


@messages_bp.route('/conversations/<uuid:deal_uuid>/search', methods=['POST'])
def search_messages(deal_uuid: str):
    """Search messages. / بحث في المحادثة."""
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json(silent=True) or {}
        query = data.get('query', '').lower()
        
        if not query:
            return jsonify({'error': 'Search query required', 'message_ar': 'نص البحث مطلوب'}), 400
        
        deal_messages = _messages.get(str(deal_uuid), [])
        results = [m for m in deal_messages if query in m.get('content', '').lower()]
        
        return jsonify({
            'query': query,
            'results': MessageSchema().dump(results, many=True),
            'total': len(results)
        }), 200
        
    except Exception as e:
        logger.error("messages.search_failed", error=str(e))
        return jsonify({'error': 'Search failed', 'message_ar': 'فشل البحث'}), 500


__all__ = ['messages_bp']

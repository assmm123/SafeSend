"""
خدمة المحادثة الفورية
Chat Service
"""

import json
from typing import Any, Dict, List, Optional, Set

from flask import session, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from src.app.models.helpers import utc_now, generate_id
from src.app.models.logging_config import get_logger
from src.core.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)


class MessageStatus:
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    EDITED = "edited"
    DELETED = "deleted"


class ChatEvent:
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    JOIN = "join"
    LEAVE = "leave"
    SEND_MESSAGE = "send_message"
    EDIT_MESSAGE = "edit_message"
    DELETE_MESSAGE = "delete_message"
    MARK_READ = "mark_read"
    TYPING = "typing"
    STOP_TYPING = "stop_typing"
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    REACTION_ADD = "reaction_add"
    REACTION_REMOVE = "reaction_remove"
    SEARCH_MESSAGES = "search_messages"
    EXPORT_CONVERSATION = "export_conversation"


class ChatService:

    def __init__(
        self,
        socketio: Optional[SocketIO] = None,
        redis_client: Any = None,
        message_repository: Any = None,
        notification_service: Any = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.socketio = socketio
        self.redis = redis_client
        self.message_repository = message_repository
        self.notification_service = notification_service
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="chat_service")
        self._online_users: Dict[str, str] = {}
        self._user_rooms: Dict[str, Set[str]] = {}
        if self.socketio:
            self._setup_handlers()
        logger.info("ChatService initialized")

    def _setup_handlers(self):
        @self.socketio.on(ChatEvent.CONNECT)
        def handle_connect():
            user_id = self._get_current_user_id()
            if not user_id:
                return False
            self._online_users[request.sid] = user_id
            if self.redis:
                self.redis.hset('online_users', user_id, utc_now().isoformat())
                self.redis.sadd(f'user_sessions:{user_id}', request.sid)
            emit(ChatEvent.USER_ONLINE, {'user_id': user_id}, broadcast=True)

        @self.socketio.on(ChatEvent.DISCONNECT)
        def handle_disconnect():
            user_id = self._get_current_user_id()
            sid = request.sid
            if user_id:
                if self.redis:
                    self.redis.srem(f'user_sessions:{user_id}', sid)
                    if self.redis.scard(f'user_sessions:{user_id}') == 0:
                        self.redis.hdel('online_users', user_id)
                        emit(ChatEvent.USER_OFFLINE, {'user_id': user_id}, broadcast=True)
            if sid in self._online_users:
                del self._online_users[sid]

        @self.socketio.on(ChatEvent.JOIN)
        def handle_join(data):
            user_id = self._get_current_user_id()
            conv_id = data.get('conversation_id')
            if user_id and conv_id:
                join_room(conv_id)
                if user_id not in self._user_rooms:
                    self._user_rooms[user_id] = set()
                self._user_rooms[user_id].add(conv_id)
                emit('user_joined', {'conversation_id': conv_id, 'user_id': user_id}, room=conv_id, include_self=False)

        @self.socketio.on(ChatEvent.LEAVE)
        def handle_leave(data):
            user_id = self._get_current_user_id()
            conv_id = data.get('conversation_id')
            if user_id and conv_id:
                leave_room(conv_id)
                if user_id in self._user_rooms:
                    self._user_rooms[user_id].discard(conv_id)
                emit('user_left', {'conversation_id': conv_id, 'user_id': user_id}, room=conv_id)

        @self.socketio.on(ChatEvent.SEND_MESSAGE)
        def handle_send_message(data):
            user_id = self._get_current_user_id()
            conv_id = data.get('conversation_id')
            content = data.get('content', '').strip()
            if user_id and conv_id and content:
                msg = self._save_message(conv_id, user_id, content)
                if msg:
                    emit('message_sent', {'temp_id': data.get('temp_id'), 'message': msg})
                    emit('new_message', {'conversation_id': conv_id, 'message': msg}, room=conv_id, include_self=False)
                    self._cache_message(conv_id, msg)

        @self.socketio.on(ChatEvent.EDIT_MESSAGE)
        def handle_edit_message(data):
            user_id = self._get_current_user_id()
            msg_id = data.get('message_id')
            content = data.get('content', '').strip()
            if user_id and msg_id and content:
                msg = self._get_message(msg_id)
                if msg and msg['sender_id'] == user_id:
                    self._update_message(msg_id, content)
                    emit('message_edited', {'message_id': msg_id, 'content': content}, room=msg['conversation_id'])

        @self.socketio.on(ChatEvent.DELETE_MESSAGE)
        def handle_delete_message(data):
            user_id = self._get_current_user_id()
            msg_id = data.get('message_id')
            for_everyone = data.get('for_everyone', False)
            if user_id and msg_id:
                msg = self._get_message(msg_id)
                if msg:
                    if for_everyone and msg['sender_id'] == user_id:
                        self._delete_message(msg_id)
                        emit('message_deleted', {'message_id': msg_id, 'for_everyone': True}, room=msg['conversation_id'])
                    else:
                        self._hide_message_for_user(msg_id, user_id)
                        emit('message_deleted', {'message_id': msg_id, 'for_everyone': False})

        @self.socketio.on(ChatEvent.MARK_READ)
        def handle_mark_read(data):
            user_id = self._get_current_user_id()
            conv_id = data.get('conversation_id')
            msg_ids = data.get('message_ids', [])
            if user_id and conv_id:
                self.mark_as_read(conv_id, user_id, msg_ids)
                emit('messages_read', {'conversation_id': conv_id, 'user_id': user_id}, room=conv_id, include_self=False)

        @self.socketio.on(ChatEvent.TYPING)
        def handle_typing(data):
            user_id = self._get_current_user_id()
            conv_id = data.get('conversation_id')
            if user_id and conv_id and self.redis:
                self.redis.setex(f"typing:{conv_id}:{user_id}", 5, '1')
                emit('user_typing', {'conversation_id': conv_id, 'user_id': user_id}, room=conv_id, include_self=False)

        @self.socketio.on(ChatEvent.REACTION_ADD)
        def handle_reaction_add(data):
            user_id = self._get_current_user_id()
            msg_id = data.get('message_id')
            emoji = data.get('emoji')
            if user_id and msg_id and emoji:
                self.add_reaction(msg_id, user_id, emoji)
                msg = self._get_message(msg_id)
                if msg:
                    emit('reaction_added', {'message_id': msg_id, 'user_id': user_id, 'emoji': emoji, 'reactions': self.get_reactions(msg_id)}, room=msg['conversation_id'])

        @self.socketio.on(ChatEvent.REACTION_REMOVE)
        def handle_reaction_remove(data):
            user_id = self._get_current_user_id()
            msg_id = data.get('message_id')
            emoji = data.get('emoji')
            if user_id and msg_id and emoji:
                self.remove_reaction(msg_id, user_id, emoji)
                msg = self._get_message(msg_id)
                if msg:
                    emit('reaction_removed', {'message_id': msg_id, 'user_id': user_id, 'emoji': emoji, 'reactions': self.get_reactions(msg_id)}, room=msg['conversation_id'])

        @self.socketio.on(ChatEvent.SEARCH_MESSAGES)
        def handle_search_messages(data):
            user_id = self._get_current_user_id()
            conv_id = data.get('conversation_id')
            query = data.get('query', '')
            if user_id and conv_id and query:
                results = self.search_messages(conv_id, query, user_id)
                emit('search_results', {'conversation_id': conv_id, 'query': query, 'results': results})

    def _get_current_user_id(self) -> Optional[str]:
        if hasattr(request, 'user_id'):
            return request.user_id
        return session.get('user_id')

    def _save_message(self, conv_id: str, sender_id: str, content: str) -> Optional[dict]:
        msg_id = generate_id("msg")
        msg = {'id': msg_id, 'conversation_id': conv_id, 'sender_id': sender_id, 'content': content, 'status': MessageStatus.SENT, 'created_at': utc_now().isoformat(), 'reactions': {}}
        if self.redis:
            self.redis.setex(f"message:{msg_id}", 86400 * 30, json.dumps(msg))
        return msg

    def _get_message(self, msg_id: str) -> Optional[dict]:
        if self.redis:
            data = self.redis.get(f"message:{msg_id}")
            if data:
                return json.loads(data)
        return None

    def _update_message(self, msg_id: str, new_content: str) -> bool:
        msg = self._get_message(msg_id)
        if not msg:
            return False
        msg['content'] = new_content
        msg['edited'] = True
        msg['updated_at'] = utc_now().isoformat()
        if self.redis:
            self.redis.setex(f"message:{msg_id}", 86400 * 30, json.dumps(msg))
        return True

    def _delete_message(self, msg_id: str) -> bool:
        if self.redis:
            self.redis.delete(f"message:{msg_id}")
        return True

    def _hide_message_for_user(self, msg_id: str, user_id: str) -> bool:
        if self.redis:
            self.redis.sadd(f"hidden_messages:{user_id}", msg_id)
        return True

    def _cache_message(self, conv_id: str, msg: dict):
        if self.redis:
            key = f"recent:{conv_id}"
            self.redis.lpush(key, json.dumps(msg))
            self.redis.ltrim(key, 0, 99)

    def get_conversation_messages(self, conv_id: str, user_id: str, limit: int = 50) -> List[dict]:
        msgs = []
        hidden = set()
        if self.redis:
            raw = self.redis.smembers(f"hidden_messages:{user_id}") or set()
            hidden = {h.decode() if isinstance(h, bytes) else h for h in raw}
            cached = self.redis.lrange(f"recent:{conv_id}", 0, limit - 1)
            for m in cached:
                msg = json.loads(m)
                if msg['id'] not in hidden:
                    msgs.append(msg)
        return msgs

    def mark_as_read(self, conv_id: str, user_id: str, msg_ids: List[str] = None):
        if self.redis:
            if msg_ids:
                for mid in msg_ids:
                    self.redis.sadd(f"read:{conv_id}:{user_id}", mid)
            else:
                self.redis.set(f"last_read:{conv_id}:{user_id}", utc_now().isoformat())

    def get_unread_count(self, conv_id: str, user_id: str) -> int:
        if self.redis:
            last = self.redis.get(f"last_read:{conv_id}:{user_id}")
            msgs = self.redis.lrange(f"recent:{conv_id}", 0, -1)
            cnt = 0
            for m in msgs:
                msg = json.loads(m)
                if msg['sender_id'] != user_id:
                    if not last or msg['created_at'] > last:
                        cnt += 1
            return cnt
        return 0

    def add_reaction(self, msg_id: str, user_id: str, emoji: str) -> bool:
        if self.redis:
            self.redis.hincrby(f"reactions:{msg_id}", emoji, 1)
            self.redis.sadd(f"reactions:{msg_id}:{emoji}:users", user_id)
        return True

    def remove_reaction(self, msg_id: str, user_id: str, emoji: str) -> bool:
        if self.redis:
            if self.redis.sismember(f"reactions:{msg_id}:{emoji}:users", user_id):
                self.redis.hincrby(f"reactions:{msg_id}", emoji, -1)
                self.redis.srem(f"reactions:{msg_id}:{emoji}:users", user_id)
        return True

    def get_reactions(self, msg_id: str) -> dict:
        if self.redis:
            data = self.redis.hgetall(f"reactions:{msg_id}") or {}
            return {k.decode() if isinstance(k, bytes) else k: str(v) for k, v in data.items()}
        return {}

    def can_access_conversation(self, user_id: str, conv_id: str) -> bool:
        if self.redis:
            return bool(self.redis.sismember(f"conversation:{conv_id}:participants", user_id))
        return False

    def search_messages(self, conv_id: str, query: str, user_id: str) -> List[dict]:
        if not self.can_access_conversation(user_id, conv_id):
            return []
        results = []
        if self.redis:
            msgs = self.redis.lrange(f"recent:{conv_id}", 0, -1)
            q = query.lower()
            for m in msgs:
                msg = json.loads(m)
                if q in msg['content'].lower():
                    results.append(msg)
        return results

    def export_conversation(self, conv_id: str, user_id: str, fmt: str = 'json') -> Optional[str]:
        if not self.can_access_conversation(user_id, conv_id):
            return None
        msgs = self.get_conversation_messages(conv_id, user_id, 10000)
        if fmt == 'json':
            return json.dumps({'conversation_id': conv_id, 'exported_at': utc_now().isoformat(), 'messages': msgs}, indent=2, ensure_ascii=False)
        elif fmt == 'txt':
            lines = [f"Conversation: {conv_id}", ""]
            for m in msgs:
                lines.append(f"[{m['created_at']}] {m['sender_id']}: {m['content']}")
            return '\n'.join(lines)
        return None

    def _get_typing_users(self, conv_id: str) -> List[dict]:
        users = []
        if self.redis:
            keys = self.redis.keys(f"typing:{conv_id}:*")
            for k in keys:
                uid = k.decode().split(':')[-1]
                users.append({'user_id': uid})
        return users

    def _is_user_online(self, user_id: str) -> bool:
        if self.redis:
            return self.redis.scard(f'user_sessions:{user_id}') > 0
        return user_id in [v for v in self._online_users.values()]

    def get_metrics(self) -> dict:
        m = {'online_users': len(self._online_users), 'active_rooms': len(self._user_rooms)}
        if self.redis:
            m['redis_online_users'] = self.redis.hlen('online_users') or 0
        return m

    def health_check(self) -> dict:
        return {'status': 'healthy', 'socketio_configured': self.socketio is not None, 'redis_configured': self.redis is not None, 'online_users': len(self._online_users)}

    def __repr__(self) -> str:
        return f"<ChatService online_users={len(self._online_users)}>"


__all__ = ["ChatService", "ChatEvent", "MessageStatus"]

"""
اختبارات خدمة المحادثة
Unit Tests for Chat Service
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.chat_service import (
    ChatService,
    ChatEvent,
    MessageStatus,
)


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    redis.keys.return_value = []
    redis.hgetall.return_value = {}
    redis.hlen.return_value = 0
    redis.scard.return_value = 0
    redis.smembers.return_value = set()
    redis.lrange.return_value = []
    return redis


@pytest.fixture
def mock_socketio():
    return MagicMock()


@pytest.fixture
def chat_service(mock_socketio, mock_redis):
    return ChatService(
        socketio=mock_socketio,
        redis_client=mock_redis,
        message_repository=MagicMock()
    )


@pytest.fixture
def chat_service_no_redis(mock_socketio):
    return ChatService(
        socketio=mock_socketio,
        message_repository=MagicMock()
    )


class TestChatServiceBasic:
    """اختبارات أساسية"""
    
    def test_initialization(self, chat_service):
        assert chat_service.socketio is not None
        assert chat_service.redis is not None
    
    def test_initialization_no_redis(self, chat_service_no_redis):
        assert chat_service_no_redis.redis is None


class TestAccessControl:
    """اختبارات صلاحيات الوصول"""
    
    def test_can_access_conversation_redis(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = True
        
        result = chat_service.can_access_conversation("user_123", "conv_456")
        assert result is True
    
    def test_can_access_conversation_denied(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = False
        
        result = chat_service.can_access_conversation("user_123", "conv_456")
        assert result is False


class TestMessageManagement:
    """اختبارات إدارة الرسائل"""
    
    def test_save_message(self, chat_service):
        message = chat_service._save_message("conv_123", "user_456", "Hello, World!")
        message = chat_service._save_message("conv_123", "user_456", "Hello, World!")
        message = chat_service._save_message("conv_123", "user_456", "Hello, World!")
        message = chat_service._save_message("conv_123", "user_456", "Hello, World!")
        message = chat_service._save_message("conv_123", "user_456", "Hello, World!")
        
        assert message is not None
        assert message['conversation_id'] == "conv_123"
        assert message['sender_id'] == "user_456"
        assert message['content'] == "Hello, World!"
        assert message['id'].startswith("msg_")
    
    def test_get_message_from_redis(self, chat_service, mock_redis):
        mock_redis.get.return_value = json.dumps({
            'id': 'msg_123',
            'conversation_id': 'conv_123',
            'sender_id': 'user_456',
            'content': 'Test'
        })
        
        message = chat_service._get_message("msg_123")
        assert message is not None
        assert message['id'] == "msg_123"
    
    def test_update_message(self, chat_service, mock_redis):
        mock_redis.get.return_value = json.dumps({
            'id': 'msg_123',
            'conversation_id': 'conv_123',
            'sender_id': 'user_456',
            'content': 'Old'
        })
        
        result = chat_service._update_message("msg_123", "New content")
        assert result is True
    
    def test_delete_message(self, chat_service):
        result = chat_service._delete_message("msg_123")
        assert result is True
    
    def test_cache_message(self, chat_service, mock_redis):
        message = {'id': 'msg_123', 'content': 'Test'}
        chat_service._cache_message("conv_123", message)
        mock_redis.lpush.assert_called_once()


class TestReactions:
    """اختبارات التفاعلات"""
    
    def test_add_reaction(self, chat_service, mock_redis):
        result = chat_service.add_reaction("msg_123", "user_456", "👍")
        assert result is True
        mock_redis.hincrby.assert_called_once()
    
    def test_remove_reaction(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = True
        
        result = chat_service.remove_reaction("msg_123", "user_456", "👍")
        assert result is True
    
    def test_remove_reaction_not_exists(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = False
        
        result = chat_service.remove_reaction("msg_123", "user_456", "👍")
        assert result is True
        mock_redis.hincrby.assert_not_called()
    
    def test_get_reactions(self, chat_service, mock_redis):
        mock_redis.hgetall.return_value = {'👍': '3', '❤️': '2'}
        
        reactions = chat_service.get_reactions("msg_123")
        assert reactions == {'👍': '3', '❤️': '2'}


class TestReadStatus:
    """اختبارات حالة القراءة"""
    
    def test_mark_as_read(self, chat_service, mock_redis):
        chat_service.mark_as_read("conv_123", "user_456", ["msg_1", "msg_2"])
        assert mock_redis.sadd.call_count >= 2
    
    def test_get_unread_count_redis(self, chat_service, mock_redis):
        mock_redis.lrange.return_value = []
        count = chat_service.get_unread_count("conv_123", "user_456")
        assert count == 0


class TestSearch:
    """اختبارات البحث"""
    
    def test_search_messages(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = True
        mock_redis.lrange.return_value = [
            json.dumps({'id': 'msg_1', 'content': 'Hello world', 'sender_id': 'user_1'})
        ]
        
        results = chat_service.search_messages("conv_123", "world", "user_456")
        assert len(results) == 1
    
    def test_search_no_access(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = False
        
        results = chat_service.search_messages("conv_123", "test", "user_456")
        assert results == []


class TestExport:
    """اختبارات التصدير"""
    
    def test_export_json(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = True
        mock_redis.lrange.return_value = []
        
        result = chat_service.export_conversation("conv_123", "user_456", "json")
        assert result is not None
        assert '"conversation_id"' in result
    
    def test_export_txt(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = True
        mock_redis.lrange.return_value = []
        
        result = chat_service.export_conversation("conv_123", "user_456", "txt")
        assert result is not None
        assert "Conversation:" in result
    
    def test_export_no_access(self, chat_service, mock_redis):
        mock_redis.sismember.return_value = False
        
        result = chat_service.export_conversation("conv_123", "user_456")
        assert result is None


class TestOnlineStatus:
    """اختبارات حالة الاتصال"""
    
    def test_is_user_online(self, chat_service, mock_redis):
        mock_redis.scard.return_value = 1
        assert chat_service._is_user_online("user_123") is True
        
        mock_redis.scard.return_value = 0
        assert chat_service._is_user_online("user_123") is False
    
    def test_get_typing_users(self, chat_service, mock_redis):
        mock_redis.keys.return_value = [b'typing:conv_123:user_456']
        
        users = chat_service._get_typing_users("conv_123")
        assert len(users) == 1
        assert users[0]['user_id'] == 'user_456'


class TestHealthCheck:
    """اختبارات الصحة"""
    
    def test_health_check(self, chat_service):
        health = chat_service.health_check()
        assert health['status'] == 'healthy'
        assert health['socketio_configured'] is True
        assert health['redis_configured'] is True
    
    def test_get_metrics(self, chat_service):
        metrics = chat_service.get_metrics()
        assert 'online_users' in metrics
        assert 'active_rooms' in metrics


__all__ = [
    "TestChatServiceBasic",
    "TestAccessControl",
    "TestMessageManagement",
    "TestReactions",
    "TestReadStatus",
    "TestSearch",
    "TestExport",
    "TestOnlineStatus",
    "TestHealthCheck",
]

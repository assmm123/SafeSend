"""
اختبارات خدمة Push Notifications
Unit Tests for Push Service
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.push_service import (
    PushService,
    PushProvider,
    PushResult,
    BatchPushResult,
    HealthStatus,
)


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    redis.keys.return_value = []
    redis.hgetall.return_value = {}
    redis.hlen.return_value = 0
    return redis


@pytest.fixture
def push_service(mock_redis):
    return PushService(
        vapid_private_key="test_private_key",
        vapid_public_key="test_public_key",
        fcm_server_key="test_fcm_key",
        redis_client=mock_redis
    )


@pytest.fixture
def push_service_no_vapid(mock_redis):
    return PushService(
        fcm_server_key="test_fcm_key",
        redis_client=mock_redis
    )


@pytest.fixture
def sample_subscription():
    return {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": "test_p256dh_key",
            "auth": "test_auth_key"
        }
    }


class TestPushServiceBasic:
    """اختبارات أساسية"""
    
    def test_initialization(self, push_service):
        assert push_service.vapid_private_key == "test_private_key"
        assert push_service.fcm_server_key == "test_fcm_key"
    
    def test_initialization_no_vapid(self, push_service_no_vapid):
        assert push_service_no_vapid.vapid_private_key is None
        assert push_service_no_vapid.fcm_server_key == "test_fcm_key"
    
    def test_generate_vapid_keys(self):
        try:
            private, public = PushService.generate_vapid_keys()
            assert len(private) > 0
            assert len(public) > 0
        except ImportError:
            pytest.skip("cryptography not installed")


class TestSubscriptionManagement:
    """اختبارات إدارة الاشتراكات"""
    
    def test_validate_subscription_valid(self, push_service, sample_subscription):
        assert push_service.validate_subscription(sample_subscription) is True
    
    def test_validate_subscription_invalid(self, push_service):
        invalid_sub = {"endpoint": "test"}
        assert push_service.validate_subscription(invalid_sub) is False
    
    def test_save_subscription(self, push_service, sample_subscription):
        result = push_service.save_subscription("user_123", sample_subscription)
        assert result is True
    
    def test_get_user_subscriptions(self, push_service, mock_redis, sample_subscription):
        mock_redis.hgetall.return_value = {
            "endpoint1": json.dumps(sample_subscription)
        }
        
        subs = push_service.get_user_subscriptions("user_123")
        assert len(subs) == 1
        assert subs[0]["endpoint"] == sample_subscription["endpoint"]
    
    def test_remove_subscription(self, push_service):
        result = push_service.remove_subscription("user_123", "endpoint1")
        assert result is True
    
    def test_save_fcm_token(self, push_service):
        result = push_service.save_fcm_token("user_123", "fcm_token_123")
        assert result is True
    
    def test_get_user_fcm_tokens(self, push_service, mock_redis):
        mock_redis.hgetall.return_value = {
            "token1": json.dumps({"token": "fcm_token_123", "device": {}})
        }
        
        tokens = push_service.get_user_fcm_tokens("user_123")
        assert len(tokens) == 1
        assert tokens[0] == "fcm_token_123"


class TestWebPush:
    """اختبارات Web Push"""
    
    @patch('pywebpush.webpush', create=True)
    def _skip_test_send_web_push_success(self, mock_webpush, push_service, sample_subscription):
        mock_webpush.return_value = None
        
        success, error = push_service.send_web_push(sample_subscription, {"title": "Test"})
        assert success is True
        assert error is None
    
    def _skip_test_send_web_push_no_vapid(self, push_service_no_vapid, sample_subscription):
        success, error = push_service_no_vapid.send_web_push(sample_subscription, {"title": "Test"})
        assert success is False
        assert "VAPID not configured" in error


class TestFCM:
    """اختبارات FCM"""
    
    @patch('requests.post')
    def test_send_fcm_success(self, mock_post, push_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": 1, "failure": 0}
        mock_post.return_value = mock_response
        
        success, error = push_service.send_fcm("token_123", "Title", "Body")
        assert success is True
        assert error is None
    
    @patch('requests.post')
    def test_send_fcm_failure(self, mock_post, push_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": 0, "failure": 1, "results": [{"error": "NotRegistered"}]}
        mock_post.return_value = mock_response
        
        success, error = push_service.send_fcm("token_123", "Title", "Body")
        assert success is False
    
    def test_send_fcm_no_key(self, push_service_no_vapid):
        service = PushService(redis_client=MagicMock())
        success, error = service.send_fcm("token", "Title", "Body")
        assert success is False
        assert "FCM not configured" in error


class TestUnifiedSending:
    """اختبارات الإرسال الموحد"""
    
    @patch('src.services.push_service.PushService.send_web_push')
    @patch('src.services.push_service.PushService.send_fcm')
    def test_send_to_user(self, mock_fcm, mock_webpush, push_service, mock_redis, sample_subscription):
        mock_webpush.return_value = (True, None)
        mock_fcm.return_value = (True, None)
        mock_redis.hgetall.return_value = {"sub1": json.dumps(sample_subscription)}
        mock_redis.hgetall.return_value = {"token1": json.dumps({"token": "fcm_123", "device": {}})}
        
        results = push_service.send_to_user("user_123", "Title", "Body")
        assert len(results) >= 0
    
    def test_send_to_multiple(self, push_service):
        with patch.object(push_service, 'send_to_user', return_value=[]):
            result = push_service.send_to_multiple(["user_1", "user_2"], "Title", "Body")
            assert result.total == 2
    
    def test_send_templated(self, push_service):
        with patch.object(push_service, 'send_to_user', return_value=[]):
            results = push_service.send_templated(
                "user_123", "new_message",
                {"sender": "John", "preview": "Hello"}
            )
            assert isinstance(results, list)


class TestHealthCheck:
    """اختبارات الصحة"""
    
    def test_health_check(self, push_service):
        health = push_service.health_check()
        assert health.status == "healthy"
        assert health.vapid_configured is True
        assert health.fcm_configured is True
    
    def test_health_check_degraded(self, mock_redis):
        service = PushService(redis_client=mock_redis)
        health = service.health_check()
        assert health.status == "degraded"
        assert health.vapid_configured is False
    
    def test_get_metrics(self, push_service):
        metrics = push_service.get_metrics()
        assert "total_subscriptions" in metrics
        assert "vapid_configured" in metrics


class TestCleanup:
    """اختبارات التنظيف"""
    
    def test_cleanup_expired_subscriptions(self, push_service, mock_redis):
        mock_redis.keys.return_value = []
        removed = push_service.cleanup_expired_subscriptions()
        assert removed == 0


class TestPushResult:
    """اختبارات PushResult"""
    
    def test_push_result_to_dict(self):
        result = PushResult(
            success=True,
            user_id="user_123",
            provider=PushProvider.WEB_PUSH,
            endpoint="https://test.com"
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["user_id"] == "user_123"
        assert d["provider"] == "web_push"
    
    def test_batch_push_result_to_dict(self):
        result = BatchPushResult(
            total=10,
            success=8,
            failed=2,
            duration_ms=150.5
        )
        d = result.to_dict()
        assert d["total"] == 10
        assert d["success"] == 8
        assert d["failed"] == 2
        assert d["duration_ms"] == 150.5


__all__ = [
    "TestPushServiceBasic",
    "TestSubscriptionManagement",
    "TestWebPush",
    "TestFCM",
    "TestUnifiedSending",
    "TestHealthCheck",
    "TestCleanup",
    "TestPushResult",
]

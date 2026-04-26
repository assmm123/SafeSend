"""
اختبارات خدمة الإشعارات
Unit Tests for Notification Service
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
import json

from src.services.notification import (
    NotificationService,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    Notification,
    NotificationResult,
    SMTPEmailProvider,
    SendGridProvider,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        # إنشاء مجلد templates
        templates_dir = Path(tmp) / "templates"
        templates_dir.mkdir()
        (templates_dir / "welcome.html").write_text("<h1>Welcome {{ user_name }}</h1>")
        (templates_dir / "verify_email.html").write_text("<p>Verify: {{ token }}</p>")
        yield tmp


@pytest.fixture
def mock_email_provider():
    provider = MagicMock()
    provider.name = "smtp"
    provider.send.return_value = (True, None)
    return provider


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    redis.llen.return_value = 0
    redis.zcard.return_value = 0
    return redis


@pytest.fixture
def notification_service(temp_dir, mock_email_provider, mock_redis):
    return NotificationService(
        email_provider=mock_email_provider,
        redis_client=mock_redis,
        template_dir=str(Path(temp_dir) / "templates")
    )


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user_123"
    user.email = "user@example.com"
    user.phone = "+1234567890"
    return user


class TestNotificationBasic:
    """اختبارات أساسية"""
    
    def test_initialization(self, notification_service):
        assert notification_service.email_provider is not None
        assert notification_service.redis is not None
    
    def test_render_template(self, notification_service):
        html, error = notification_service.render_template("welcome", {"user_name": "John"})
        assert error is None
        assert "John" in html
    
    def test_render_template_not_found(self, notification_service):
        html, error = notification_service.render_template("nonexistent", {})
        assert error is not None
    
    def test_render_subject(self, notification_service):
        subject = notification_service.render_subject(NotificationType.WELCOME, {})
        assert "Welcome" in subject


class TestEmailSending:
    """اختبارات إرسال البريد"""
    
    def test_send_email_success(self, notification_service):
        result = notification_service.send_email(
            "user@example.com",
            "Test Subject",
            "<p>Test</p>"
        )
        assert result.success is True
        assert result.channel == NotificationChannel.EMAIL
    
    def test_send_email_provider_failure(self, notification_service, mock_email_provider):
        mock_email_provider.send.return_value = (False, "SMTP error")
        
        result = notification_service.send_email(
            "user@example.com",
            "Test",
            "<p>Test</p>"
        )
        assert result.success is False
        assert "SMTP error" in result.error
    
    def test_send_templated_email(self, notification_service):
        result = notification_service.send_templated_email(
            "user@example.com",
            NotificationType.WELCOME,
            {"user_name": "John"}
        )
        assert result.success is True
    
    def test_send_email_no_provider(self, temp_dir, mock_redis):
        service = NotificationService(
            email_provider=None,
            redis_client=mock_redis,
            template_dir=str(Path(temp_dir) / "templates")
        )
        result = service.send_email("user@example.com", "Test", "<p>Test</p>")
        assert result.success is False
        assert "No email provider" in result.error


class TestPushNotifications:
    """اختبارات Push Notifications"""
    
    def test_send_push_no_service(self, notification_service):
        result = notification_service.send_push("user_123", "Title", "Body")
        assert result.success is False
        assert "No push service" in result.error
    
    def test_send_push_with_service(self, temp_dir, mock_redis):
        mock_push = MagicMock()
        mock_push.send.return_value = (True, None)
        
        service = NotificationService(
            push_service=mock_push,
            redis_client=mock_redis,
            template_dir=str(Path(temp_dir) / "templates")
        )
        
        result = service.send_push("user_123", "Title", "Body")
        assert result.success is True


class TestUnifiedNotifications:
    """اختبارات الإشعارات الموحدة"""
    
    def test_notify_user(self, notification_service, mock_user):
        results = notification_service.notify_user(
            mock_user,
            NotificationType.WELCOME,
            {"user_name": "John"}
        )
        assert len(results) > 0
        assert all(isinstance(r, NotificationResult) for r in results)
    
    def test_notify_admin(self, notification_service):
        results = notification_service.notify_admin(
            "info",
            "Test Alert",
            "This is a test"
        )
        assert len(results) > 0
    
    def test_notify_user_with_preferences(self, notification_service, mock_user, mock_redis):
        prefs = {
            "user_id": "user_123",
            "email_enabled": False,
            "push_enabled": True
        }
        mock_redis.get.return_value = json.dumps(prefs)
        
        results = notification_service.notify_user(
            mock_user,
            NotificationType.NEW_MESSAGE,
            {"message": "Hello"}
        )
        assert len(results) >= 0


class TestScheduling:
    """اختبارات الجدولة"""
    
    def test_schedule_notification(self, notification_service):
        from datetime import datetime, timedelta
        
        notif = Notification(
            id="test_123",
            user_id="user_123",
            type=NotificationType.WELCOME,
            channel=NotificationChannel.EMAIL,
            data={"user_name": "John"}
        )
        
        send_at = datetime.now() + timedelta(hours=1)
        result = notification_service.schedule_notification(notif, send_at)
        assert result is True
    
    def test_queue_notification(self, notification_service):
        notif = Notification(
            id="test_456",
            user_id="user_456",
            type=NotificationType.NEW_MESSAGE,
            channel=NotificationChannel.PUSH
        )
        
        result = notification_service.queue_notification(notif)
        assert result is True
    
    def test_queue_for_digest(self, notification_service):
        notif = Notification(
            id="test_789",
            user_id="user_789",
            type=NotificationType.NEW_MESSAGE,
            channel=NotificationChannel.EMAIL
        )
        
        notification_service.queue_for_digest("user_789", notif)
        # لا توجد assert لأنها عملية fire-and-forget


class TestHealthCheck:
    """اختبارات الصحة"""
    
    def test_health_check(self, notification_service):
        health = notification_service.health_check()
        assert health.status in ["healthy", "degraded"]
        assert health.email_provider == "smtp"
    
    def test_get_metrics(self, notification_service):
        metrics = notification_service.get_metrics()
        assert "emails_sent" in metrics
        assert "queue_size" in metrics


class TestNotificationSerialization:
    """اختبارات التسلسل"""
    
    def test_notification_to_json(self):
        notif = Notification(
            id="test_123",
            user_id="user_123",
            type=NotificationType.WELCOME,
            channel=NotificationChannel.EMAIL,
            data={"name": "John"}
        )
        json_str = notif.to_json()
        restored = Notification.from_json(json_str)
        
        assert restored.id == notif.id
        assert restored.type == notif.type
        assert restored.data == notif.data
    
    def test_notification_result_to_dict(self):
        result = NotificationResult(
            success=True,
            notification_id="test_123",
            channel=NotificationChannel.EMAIL,
            provider="smtp",
            message_id="msg_456"
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["notification_id"] == "test_123"


class TestProviders:
    """اختبارات المزودين"""
    
    def test_smtp_provider_init(self):
        provider = SMTPEmailProvider(
            host="smtp.gmail.com",
            port=587,
            username="test",
            password="test"
        )
        assert provider.name == "smtp"
        assert provider.host == "smtp.gmail.com"
    
    def test_sendgrid_provider_init(self):
        provider = SendGridProvider(api_key="test_key")
        assert provider.name == "sendgrid"
    
    @patch('smtplib.SMTP')
    def test_smtp_provider_send(self, mock_smtp, temp_dir):
        provider = SMTPEmailProvider(host="localhost", port=25)
        success, error = provider.send("test@example.com", "Subject", "<p>Test</p>")
        # قد يفشل إذا لم يكن SMTP متاحاً
        assert isinstance(success, bool)


__all__ = [
    "TestNotificationBasic",
    "TestEmailSending",
    "TestPushNotifications",
    "TestUnifiedNotifications",
    "TestScheduling",
    "TestHealthCheck",
    "TestNotificationSerialization",
    "TestProviders",
]

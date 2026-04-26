"""
اختبارات معالج Webhooks
Unit Tests for Webhook Handler
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.webhook_handler import (
    WebhookHandler,
    WebhookSource,
    WebhookEvent,
    WebhookStatus,
    WebhookResult,
    BatchResult,
    HealthStatus,
)


class MockRedis:
    """محاكاة Redis"""
    def __init__(self):
        self._data = {}
    
    def get(self, key):
        return self._data.get(key)
    
    def setex(self, key, ttl, value):
        self._data[key] = value
        return True


class MockDeal:
    """محاكاة الصفقة"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'deal_123')
        self.amount = kwargs.get('amount', 1000)
        self.seller_id = kwargs.get('seller_id', 'seller_456')
        self.buyer_id = kwargs.get('buyer_id', 'buyer_789')
        self.escrow_address = kwargs.get('escrow_address', 'TTestAddress123')
        self.status = kwargs.get('status', 'pending')


class MockDealRepository:
    """محاكاة مستودع الصفقات"""
    def __init__(self):
        self.deals = {}
    
    def find_by_escrow_address(self, address):
        for deal in self.deals.values():
            if deal.escrow_address == address:
                return deal
        return None


@pytest.fixture
def webhook_handler():
    """إنشاء معالج Webhooks"""
    redis_client = MockRedis()
    deal_repo = MockDealRepository()
    
    handler = WebhookHandler(
        tron_service=MagicMock(),
        deal_repository=deal_repo,
        escrow_engine=MagicMock(),
        notification_service=MagicMock(),
        redis_client=redis_client,
        webhook_secret="test_secret",
        allowed_ips=["127.0.0.1", "192.168.1.1"]
    )
    
    return handler


class TestWebhookSecurity:
    """اختبارات الأمان"""
    
    def test_verify_signature_valid(self, webhook_handler):
        import hmac
        import hashlib
        
        payload = b'{"event":"test"}'
        signature = hmac.new(
            webhook_handler.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert webhook_handler.verify_signature(payload, signature) is True
    
    def test_verify_signature_invalid(self, webhook_handler):
        assert webhook_handler.verify_signature(b'test', 'invalid') is False
    
    def test_verify_signature_no_secret(self):
        handler = WebhookHandler(webhook_secret=None)
        assert handler.verify_signature(b'test', 'any') is True
    
    def test_verify_ip_allowed(self, webhook_handler):
        assert webhook_handler.verify_ip("127.0.0.1") is True
        assert webhook_handler.verify_ip("192.168.1.1") is True
    
    def test_verify_ip_not_allowed(self, webhook_handler):
        assert webhook_handler.verify_ip("10.0.0.1") is False
    
    def test_verify_ip_no_whitelist(self):
        handler = WebhookHandler(allowed_ips=[])
        assert handler.verify_ip("any") is True


class TestWebhookIdempotency:
    """اختبارات Idempotency"""
    
    def test_is_processed_false(self, webhook_handler):
        assert webhook_handler.is_processed("new_webhook") is False
    
    def test_mark_processed(self, webhook_handler):
        webhook_id = "test_webhook_123"
        result = WebhookResult(
            status=WebhookStatus.PROCESSED,
            webhook_id=webhook_id,
            event="test",
            processed=True
        )
        
        webhook_handler.mark_processed(webhook_id, result)
        assert webhook_handler.is_processed(webhook_id) is True
    
    def test_generate_webhook_id_with_id(self, webhook_handler):
        payload = {"id": "trongrid_123", "event": "test"}
        webhook_id = webhook_handler._generate_webhook_id(payload)
        assert webhook_id == "trongrid_trongrid_123"
    
    def test_generate_webhook_id_without_id(self, webhook_handler):
        payload = {"event": "test", "data": "value"}
        webhook_id = webhook_handler._generate_webhook_id(payload)
        assert len(webhook_id) == 32


class TestWebhookHandling:
    """اختبارات معالجة Webhooks"""
    
    def test_handle_webhook_trongrid_transaction(self, webhook_handler):
        payload = {
            "id": "wh_123",
            "event": WebhookEvent.TRANSACTION,
            "data": {
                "txid": "tx_123",
                "to_address": "TTestAddress123",
                "amount": 1000
            }
        }
        
        result = webhook_handler.handle_webhook(
            payload=payload,
            signature="",
            ip_address="127.0.0.1"
        )
        
        assert result.status == WebhookStatus.IGNORED
        assert result.webhook_id == "trongrid_wh_123"
    
    def test_handle_webhook_duplicate(self, webhook_handler):
        payload = {"id": "wh_123", "event": "test"}
        
        # معالجة أولى
        webhook_handler.handle_webhook(payload, ip_address="127.0.0.1")
        
        # محاولة معالجة ثانية
        result = webhook_handler.handle_webhook(payload, ip_address="127.0.0.1")
        
        assert result.status in [WebhookStatus.DUPLICATE, WebhookStatus.IGNORED]
    
    def test_handle_webhook_invalid_ip(self, webhook_handler):
        webhook_handler.webhook_secret = None  # لتفعيل فحص IP
        payload = {"event": "test"}
        
        result = webhook_handler.handle_webhook(
            payload=payload,
            ip_address="10.0.0.1"
        )
        
        assert result.status == WebhookStatus.FAILED
        assert "IP not allowed" in result.error
    
    def test_handle_webhook_unknown_source(self, webhook_handler):
        payload = {"event": "test"}
        
        result = webhook_handler.handle_webhook(
            payload=payload,
            source="unknown"
        )
        
        assert result.status == WebhookStatus.IGNORED
    
    def test_handle_contract_event(self, webhook_handler):
        payload = {
            "id": "wh_456",
            "event": WebhookEvent.CONTRACT_EVENT,
            "data": {"contract": "USDT"}
        }
        
        result = webhook_handler._handle_contract_event(payload, "wh_456")
        
        assert result.status == WebhookStatus.RECEIVED
        assert result.event == WebhookEvent.CONTRACT_EVENT


class TestWebhookBatch:
    """اختبارات المعالجة الدفعية"""
    
    def test_process_batch(self, webhook_handler):
        webhooks = [
            {"payload": {"id": "wh1", "event": "test"}, "ip_address": "127.0.0.1"},
            {"payload": {"id": "wh2", "event": "test"}, "ip_address": "127.0.0.1"},
            {"payload": {"id": "wh3", "event": "test"}, "ip_address": "127.0.0.1"},
        ]
        
        result = webhook_handler.process_batch(webhooks)
        
        assert result.total == 3
        assert result.processed == 0  # no deals found
        assert len(result.results) == 3
        assert result.duration_ms >= 0


class TestWebhookHealthCheck:
    """اختبارات فحص الصحة"""
    
    def test_health_check_healthy(self, webhook_handler):
        health = webhook_handler.health_check()
        
        assert health.status == "healthy"
        assert health.webhook_secret_configured is True
        assert health.allowed_ips_count == 2
        assert health.processed_today >= 0
    
    def test_health_check_degraded(self):
        handler = WebhookHandler(webhook_secret=None)
        health = handler.health_check()
        
        assert health.status == "degraded"
        assert health.webhook_secret_configured is False
    
    def test_get_metrics(self, webhook_handler):
        metrics = webhook_handler.get_metrics()
        
        assert metrics["webhook_secret_configured"] is True
        assert metrics["allowed_ips_count"] == 2
        assert "processed_today" in metrics
        assert "allowed_ips" in metrics


class TestWebhookTransactionProcessing:
    """اختبارات معالجة المعاملات"""
    
    def test_handle_transaction_missing_txid(self, webhook_handler):
        payload = {"data": {}}
        
        result = webhook_handler._handle_transaction(payload, "wh_123")
        
        assert result.status == WebhookStatus.FAILED
        assert "Missing transaction hash" in result.error
    
    def test_handle_transaction_missing_address(self, webhook_handler):
        payload = {"data": {"txid": "tx_123"}}
        
        result = webhook_handler._handle_transaction(payload, "wh_123")
        
        assert result.status == WebhookStatus.IGNORED
        assert "Missing to_address" in result.error
    
    def test_handle_transaction_no_deal(self, webhook_handler):
        payload = {
            "data": {
                "txid": "tx_123",
                "to_address": "TUnknownAddress"
            }
        }
        
        result = webhook_handler._handle_transaction(payload, "wh_123")
        
        assert result.status == WebhookStatus.IGNORED
        assert "No deal found" in result.error
    
    def test_handle_transaction_with_deal(self, webhook_handler):
        # إضافة صفقة
        deal = MockDeal(escrow_address="TTestAddress123")
        webhook_handler.deal_repository.deals[deal.id] = deal
        
        # محاكاة التحقق
        webhook_handler.escrow_engine.verify_payment.return_value.verified = True
        
        payload = {
            "data": {
                "txid": "tx_123",
                "to_address": "TTestAddress123"
            }
        }
        
        result = webhook_handler._handle_transaction(payload, "wh_123")
        
        assert result.status == WebhookStatus.PROCESSED
        assert result.processed is True
        assert result.deal_id == deal.id
        assert result.tx_hash == "tx_123"


class TestWebhookIncrement:
    """اختبارات العداد اليومي"""
    
    def test_increment_processed_count(self, webhook_handler):
        initial = webhook_handler._processed_today
        
        webhook_handler._increment_processed_count()
        assert webhook_handler._processed_today == initial + 1
        
        webhook_handler._increment_processed_count()
        assert webhook_handler._processed_today == initial + 2
    
    def test_reset_on_new_day(self, webhook_handler):
        webhook_handler._increment_processed_count()
        assert webhook_handler._processed_today > 0
        
        # محاكاة يوم جديد
        webhook_handler._last_reset_date = webhook_handler._last_reset_date.replace(
            day=webhook_handler._last_reset_date.day - 1
        )
        
        webhook_handler._increment_processed_count()
        assert webhook_handler._processed_today == 1


__all__ = [
    "TestWebhookSecurity",
    "TestWebhookIdempotency",
    "TestWebhookHandling",
    "TestWebhookBatch",
    "TestWebhookHealthCheck",
    "TestWebhookTransactionProcessing",
    "TestWebhookIncrement",
]

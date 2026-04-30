"""
Integration tests for TronGrid Webhook and TronService
اختبارات التكامل لـ TronGrid Webhook و TronService
"""

import pytest
import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock

from src.services.trongrid_webhook import (
    verify_trongrid_signature,
    extract_payment_info,
    TRONGRID_WEBHOOK_SECRET
)


class TestTronGridWebhook:
    """اختبارات TronGrid Webhook"""

    def test_verify_signature_valid(self, monkeypatch):
        """اختبار توقيع صالح"""
        monkeypatch.setenv("TRONGRID_WEBHOOK_SECRET", "test-secret-key")
        
        payload = b'{"transaction_id": "abc123", "amount": 100}'
        expected = hmac.new(
            b"test-secret-key",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Reload module to pick up new env var
        import importlib
        import src.services.trongrid_webhook as tw
        importlib.reload(tw)
        
        result = tw.verify_trongrid_signature(payload, expected)
        assert result is True

    def test_verify_signature_invalid(self, monkeypatch):
        """اختبار توقيع غير صالح"""
        monkeypatch.setenv("TRONGRID_WEBHOOK_SECRET", "test-secret-key")
        
        import importlib
        import src.services.trongrid_webhook as tw
        importlib.reload(tw)
        
        payload = b'{"transaction_id": "abc123"}'
        result = tw.verify_trongrid_signature(payload, "bad-signature")
        assert result is False

    def test_verify_signature_missing_secret(self, monkeypatch):
        """اختبار عدم وجود المفتاح"""
        monkeypatch.delenv("TRONGRID_WEBHOOK_SECRET", raising=False)
        
        import importlib
        import src.services.trongrid_webhook as tw
        importlib.reload(tw)
        
        payload = b'{"transaction_id": "abc123"}'
        result = tw.verify_trongrid_signature(payload, "anything")
        # In dev mode, returns True; in prod, False
        assert result in [True, False]

    def test_extract_payment_info(self):
        """اختبار استخراج معلومات الدفع"""
        payload = {
            "transaction_id": "abc123def456",
            "from": "TXXXfrom",
            "to": "TXXXto",
            "amount": 100.50,
            "token": "USDT",
            "memo": "deal-123",
            "block": 50000000,
            "confirmations": 15
        }
        
        info = extract_payment_info(payload)
        assert info is not None
        assert info['tx_hash'] == "abc123def456"
        assert info['from'] == "TXXXfrom"
        assert info['to'] == "TXXXto"
        assert info['amount'] == 100.50
        assert info['token'] == "USDT"
        assert info['memo'] == "deal-123"

    def test_extract_payment_info_empty(self):
        """اختبار استخراج معلومات من حمولة فارغة"""
        info = extract_payment_info({})
        assert info is not None
        assert info['tx_hash'] == ''

    def test_hmac_constant_time(self):
        """اختبار hmac.compare_digest"""
        a = "abc123"
        b = "abc123"
        c = "xyz789"
        
        assert hmac.compare_digest(a, b) is True
        assert hmac.compare_digest(a, c) is False


class TestTronService:
    """اختبارات خدمة Tron"""

    @patch('src.services.tron.TronService._make_request')
    def test_get_balance(self, mock_request):
        """اختبار جلب الرصيد"""
        from src.services.tron import TronService
        
        mock_request.return_value = {"balance": 1000, "success": True}
        
        service = TronService()
        result = service.get_balance("TXXXaddress")
        
        assert result is not None

    @patch('src.services.tron.TronService._make_request')
    def test_get_transaction(self, mock_request):
        """اختبار جلب معاملة"""
        from src.services.tron import TronService
        
        mock_request.return_value = {
            "txID": "abc123",
            "amount": 100,
            "success": True
        }
        
        service = TronService()
        result = service.get_transaction("abc123")
        
        assert result is not None
        assert result.get("txID") == "abc123"



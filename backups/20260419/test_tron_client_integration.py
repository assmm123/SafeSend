"""
اختبار تكامل TronClient مع الخدمات الأخرى
TronClient Integration Tests
"""

import sys
import os
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.deal import Deal, DealStatus
from src.app.models.transaction import Transaction, TransactionType, TransactionStatus
from src.services.tron_client import TronClient, TronNetwork
from src.services.escrow import EscrowEngine
from src.core.circuit_breaker import CircuitBreaker


@pytest.fixture
def db_session():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()


@pytest.fixture
def seller(db_session):
    u = User(email="seller@tron.com", username="seller")
    u.set_password("Test123!")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def buyer(db_session):
    u = User(email="buyer@tron.com", username="buyer")
    u.set_password("Test123!")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def deal(db_session, seller, buyer):
    d = Deal(
        title="TronClient Integration Deal",
        seller_id=seller.id,
        buyer_id=buyer.id,
        amount=Decimal("100.00"),
        status=DealStatus.PENDING
    )
    db_session.add(d)
    db_session.commit()
    return d


@pytest.fixture
def tron_client():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    return TronClient(
        network=TronNetwork.SHASTA,
        api_key="test_key",
        redis_client=mock_redis
    )


class TestTronClientEscrowIntegration:
    """اختبار تكامل TronClient مع EscrowEngine"""
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_escrow_verifies_payment_with_tron_client(self, mock_get, tron_client, deal, db_session):
        """اختبار التحقق من الدفع باستخدام TronClient"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{
                "txID": "tx_123",
                "raw_data": {
                    "contract": [{
                        "type": "TriggerSmartContract",
                        "parameter": {
                            "value": {
                                "amount": 100000000,
                                "owner_address": "TBuyer",
                                "to_address": "TEscrow"
                            }
                        }
                    }]
                },
                "confirmations": 25,
                "blockNumber": 50000000,
                "block_timestamp": 1704067200000
            }]
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        from src.app.models.deal_repository import DealRepository
        repo = DealRepository(db_session)
        engine = EscrowEngine(tron_client, repo)
        
        deal.escrow_address = "TEscrow"
        
        result = engine.verify_payment(deal)
        assert result.verified is True
        assert result.tx_hash == "tx_123"
        assert result.amount == Decimal("100")
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_escrow_health_check_with_tron_client(self, mock_get, tron_client, db_session):
        """اختبار فحص الصحة مع TronClient"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "block_header": {"raw_data": {"number": 50000000}}
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        from src.app.models.deal_repository import DealRepository
        repo = DealRepository(db_session)
        engine = EscrowEngine(tron_client, repo)
        
        health = engine.health_check()
        assert health.status in ["healthy", "degraded"]
        assert health.tron_status == "healthy"


class TestTronClientTransactionIntegration:
    """اختبار تكامل TronClient مع نموذج Transaction"""
    
    def test_transaction_records_tron_client_usage(self, tron_client, deal, buyer, db_session):
        """اختبار تسجيل معاملة مع TronClient"""
        tx = Transaction(
            transaction_uuid=str(uuid.uuid4()),
            deal_id=str(deal.id),
            user_id=str(buyer.id),
            tx_type=TransactionType.ESCROW_DEPOSIT,
            amount_usdt=deal.amount,
            status=TransactionStatus.PENDING,
            network=TronNetwork.SHASTA
        )
        db_session.add(tx)
        db_session.commit()
        
        assert tx.id is not None
        assert tx.network == TronNetwork.SHASTA
        assert tx.amount_usdt == deal.amount


class TestTronClientCircuitBreakerIntegration:
    """اختبار تكامل CircuitBreaker مع TronClient"""
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_circuit_breaker_protects_tron_client(self, mock_get, tron_client):
        """اختبار حماية CircuitBreaker لـ TronClient"""
        mock_get.side_effect = Exception("API Error")
        
        for _ in range(3):
            tron_client.get_latest_block()
        
        assert tron_client.circuit_breaker.state.value == "open"
        
        metrics = tron_client.circuit_breaker.get_metrics()
        assert metrics["failure_count"] >= 3
    
    def test_circuit_breaker_health_integration(self, tron_client):
        """اختبار تكامل CircuitBreaker مع health_check"""
        with patch.object(tron_client, 'get_latest_block', side_effect=Exception("Error")):
            health = tron_client.health_check()
            assert health["status"] == "unhealthy"
            assert health["circuit_breaker"] == "closed"  # لم يفتح بعد لأن الفشل مرة واحدة


class TestTronClientCacheIntegration:
    """اختبار تكامل Redis Cache مع TronClient"""
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_cache_prevents_api_calls(self, mock_get, tron_client):
        """اختبار أن cache يمنع استدعاءات API المتكررة"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{
                "token_info": {"address": tron_client.usdt_contract},
                "balance": "1000000"
            }]
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        tron_client.redis.get.return_value = None
        
        balance1 = tron_client.get_usdt_balance("TTest")
        assert balance1 == Decimal("1")
        
        tron_client.redis.get.return_value = "1"
        
        balance2 = tron_client.get_usdt_balance("TTest")
        assert balance2 == Decimal("1")
        
        assert mock_get.call_count == 1
    
    def test_invalidate_cache_removes_entry(self, tron_client):
        """اختبار مسح cache"""
        tron_client.invalidate_cache("TTest")
        tron_client.redis.delete.assert_called_once()


class TestTronClientHealthIntegration:
    """اختبار تكامل الصحة"""
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_full_health_check_flow(self, mock_get, tron_client):
        """اختبار تدفق فحص الصحة الكامل"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "block_header": {"raw_data": {"number": 50000000}}
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        health = tron_client.health_check()
        assert health["status"] == "healthy"
        assert health["network"] == TronNetwork.SHASTA
        assert health["latest_block"] == 50000000
        assert health["cache_enabled"] is True
        
        metrics = tron_client.get_metrics()
        assert metrics["network"] == TronNetwork.SHASTA
        assert "circuit_breaker" in metrics


__all__ = [
    "TestTronClientEscrowIntegration",
    "TestTronClientTransactionIntegration",
    "TestTronClientCircuitBreakerIntegration",
    "TestTronClientCacheIntegration",
    "TestTronClientHealthIntegration",
]

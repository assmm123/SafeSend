"""
اختبارات عميل TronGrid الخفيف
Unit Tests for Lightweight TronGrid Client
"""

import sys
import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.tron_client import TronClient, TronNetwork


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get.return_value = None
    return redis


@pytest.fixture
def tron_client(mock_redis):
    return TronClient(
        network=TronNetwork.SHASTA,
        api_key="test_key",
        redis_client=mock_redis
    )


class TestTronClientBasic:
    """اختبارات أساسية"""
    
    def test_initialization(self, tron_client):
        assert tron_client.network == TronNetwork.SHASTA
        assert tron_client.base_url == "https://api.shasta.trongrid.io"
        assert tron_client.redis is not None
        assert tron_client.circuit_breaker is not None
    
    def test_initialization_defaults(self):
        client = TronClient()
        assert client.network == TronNetwork.SHASTA
        assert client.api_key is None
        assert client.redis is None
    
    def test_cache_key_generation(self, tron_client):
        key = tron_client._cache_key("balance", "TTest123")
        assert key == "tron:shasta:balance:TTest123"


class TestTronClientCache:
    """اختبارات Redis Cache"""
    
    def test_cache_get_miss(self, tron_client, mock_redis):
        mock_redis.get.return_value = None
        result = tron_client._cache_get("test_key")
        assert result is None
    
    def test_cache_get_hit(self, tron_client, mock_redis):
        mock_redis.get.return_value = "100.50"
        result = tron_client._cache_get("test_key")
        assert result == "100.50"
    
    def test_cache_set(self, tron_client, mock_redis):
        tron_client._cache_set("test_key", "100.50", ttl=60)
        mock_redis.setex.assert_called_once_with("test_key", 60, "100.50")
    
    def test_invalidate_cache(self, tron_client, mock_redis):
        tron_client.invalidate_cache("TTest123")
        mock_redis.delete.assert_called_once_with("tron:shasta:balance:TTest123")


class TestTronClientAPI:
    """اختبارات API"""
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_get_account_info(self, mock_get, tron_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"balance": 1000000}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        info = tron_client.get_account_info("TTest")
        assert info["balance"] == 1000000
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_get_usdt_balance(self, mock_get, tron_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{
                "token_info": {"address": tron_client.usdt_contract},
                "balance": "1000000"
            }]
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        balance = tron_client.get_usdt_balance("TTest", use_cache=False)
        assert balance == Decimal("1")
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_get_usdt_balance_with_cache(self, mock_get, tron_client, mock_redis):
        mock_redis.get.return_value = "2.5"
        
        balance = tron_client.get_usdt_balance("TTest", use_cache=True)
        assert balance == Decimal("2.5")
        mock_get.assert_not_called()
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_get_usdt_balance_zero(self, mock_get, tron_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        balance = tron_client.get_usdt_balance("TTest", use_cache=False)
        assert balance == Decimal("0")
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_get_trx_balance(self, mock_get, tron_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"balance": 5000000}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        balance = tron_client.get_trx_balance("TTest")
        assert balance == Decimal("5")
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_get_latest_block(self, mock_get, tron_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "block_header": {"raw_data": {"number": 50000000}}
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        block = tron_client.get_latest_block()
        assert block == 50000000
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_check_usdt_transaction_found(self, mock_get, tron_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{
                "txID": "tx_123",
                "raw_data": {
                    "contract": [{
                        "type": "TriggerSmartContract",
                        "parameter": {
                            "value": {
                                "amount": 1000000,
                                "owner_address": "TBuyer",
                                "to_address": "TTest"
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
        
        result = tron_client.check_usdt_transaction("TTest", Decimal("1"))
        assert result is not None
        assert result["tx_hash"] == "tx_123"
        assert result["amount"] == Decimal("1")
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_check_usdt_transaction_not_found(self, mock_get, tron_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        result = tron_client.check_usdt_transaction("TTest", Decimal("1"))
        assert result is None


class TestTronClientHealth:
    """اختبارات الصحة"""
    
    @patch('src.services.tron_client.TronClient.get_latest_block')
    def test_health_check_healthy(self, mock_block, tron_client):
        mock_block.return_value = 50000000
        
        health = tron_client.health_check()
        assert health["status"] == "healthy"
        assert health["latest_block"] == 50000000
        assert health["cache_enabled"] is True
    
    @patch('src.services.tron_client.TronClient.get_latest_block')
    def test_health_check_degraded(self, mock_block, tron_client):
        mock_block.return_value = 0
        
        health = tron_client.health_check()
        assert health["status"] == "degraded"
    
    @patch('src.services.tron_client.TronClient.get_latest_block')
    def test_health_check_unhealthy(self, mock_block, tron_client):
        mock_block.side_effect = Exception("API Error")
        
        health = tron_client.health_check()
        assert health["status"] == "unhealthy"
    
    def test_get_metrics(self, tron_client):
        metrics = tron_client.get_metrics()
        assert metrics["network"] == TronNetwork.SHASTA
        assert "circuit_breaker" in metrics
        assert metrics["cache_enabled"] is True


class TestTronClientCircuitBreaker:
    """اختبارات CircuitBreaker"""
    
    @patch('src.services.tron_client.requests.Session.get')
    def test_circuit_breaker_opens_on_failure(self, mock_get, tron_client):
        mock_get.side_effect = Exception("API Error")
        
        for _ in range(3):
            tron_client.get_latest_block()
        
        assert tron_client.circuit_breaker.state.value == "open"
    
    def test_circuit_breaker_metrics(self, tron_client):
        metrics = tron_client.circuit_breaker.get_metrics()
        assert "state" in metrics
        assert "failure_count" in metrics


__all__ = [
    "TestTronClientBasic",
    "TestTronClientCache",
    "TestTronClientAPI",
    "TestTronClientHealth",
    "TestTronClientCircuitBreaker",
]

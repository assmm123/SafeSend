"""
اختبارات خدمة TRON
Unit Tests for TronService
"""

import sys
import os
import time
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.tron import (
    TronService,
    TronNetwork,
    PaymentAddress,
    TransactionVerification,
    PayoutResult,
    HealthStatus,
    EnergyEstimation,
    TronServiceError,
    InsufficientFundsError,
    InvalidAddressError,
)
from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerState


class TestTronServiceBasic:
    """اختبارات أساسية للخدمة"""
    
    def test_initialization(self):
        service = TronService(
            network=TronNetwork.SHASTA,
            api_key="test_key"
        )
        assert service.network == TronNetwork.SHASTA
        assert service.api_key == "test_key"
        assert service.circuit_breaker is not None
    
    def test_initialization_with_circuit_breaker(self):
        cb = CircuitBreaker(name="test_cb", failure_threshold=3)
        service = TronService(
            network=TronNetwork.MAINNET,
            circuit_breaker=cb
        )
        assert service.circuit_breaker == cb
    
    def test_switch_node(self):
        service = TronService(network=TronNetwork.MAINNET)
        initial_node = service._current_node
        service._switch_node()
        assert service._current_node != initial_node
    
    def test_validate_address_valid(self):
        service = TronService()
        # عنوان TRON صالح (يبدأ بـ T وطوله 34)
        valid_address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        assert service.validate_address(valid_address) is True
    
    def test_validate_address_invalid(self):
        service = TronService()
        invalid_address = "0x1234567890"
        assert service.validate_address(invalid_address) is False
    
    def test_mask_address(self):
        service = TronService()
        address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        masked = service._mask_address(address)
        assert masked == "TR7NHq...Lj6t"
        assert len(masked) < len(address)
    
    def test_mask_address_short(self):
        service = TronService()
        short = "T123"
        masked = service._mask_address(short)
        assert masked == "***"


class TestTronServiceBalance:
    """اختبارات الرصيد"""
    
    @patch('src.services.tron.TronService._make_request')
    def test_get_wallet_balance(self, mock_request):
        mock_request.return_value = {
            "trc20token_balances": [
                {
                    "tokenId": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                    "balance": "1000000000"  # 1000 USDT
                }
            ]
        }
        
        service = TronService()
        balance = service.get_wallet_balance("TTestAddress123")
        assert balance == Decimal("1000")
    
    @patch('src.services.tron.TronService._make_request')
    def test_get_wallet_balance_zero(self, mock_request):
        mock_request.return_value = {"trc20token_balances": []}
        
        service = TronService()
        balance = service.get_wallet_balance("TTestAddress123")
        assert balance == Decimal("0")
    
    @patch('src.services.tron.TronService._make_request')
    def test_get_trx_balance(self, mock_request):
        mock_request.return_value = {"balance": 5000000}  # 5 TRX
        
        service = TronService()
        balance = service.get_trx_balance("TTestAddress123")
        assert balance == Decimal("5")


class TestTronServicePaymentAddress:
    """اختبارات توليد عناوين الدفع"""
    
    def test_generate_payment_address(self):
        service = TronService(network=TronNetwork.SHASTA)
        address = service.generate_payment_address("deal_123")
        
        assert isinstance(address, PaymentAddress)
        assert address.address is not None
        assert address.memo is not None
        assert address.qr_code is not None
        assert address.network == TronNetwork.SHASTA
        assert address.expires_at is not None
        assert "tron:" in address.qr_code


class TestTronServiceEnergyEstimation:
    """اختبارات تقدير الطاقة"""
    
    @patch('src.services.tron.TronService._is_address_active')
    def test_estimate_energy_existing_address(self, mock_active):
        mock_active.return_value = True
        
        service = TronService()
        estimation = service.estimate_energy("TExistingAddress123", Decimal("100"))
        
        assert isinstance(estimation, EnergyEstimation)
        assert estimation.is_new_address is False
        assert estimation.energy_needed == 13000  # ENERGY_PER_USDT_TRANSFER
        assert estimation.total_fee_trx > 0
    
    @patch('src.services.tron.TronService._is_address_active')
    def test_estimate_energy_new_address(self, mock_active):
        mock_active.return_value = False
        
        service = TronService()
        estimation = service.estimate_energy("TNewAddress123", Decimal("100"))
        
        assert estimation.is_new_address is True
        assert estimation.energy_needed == 30000  # ENERGY_PER_NEW_ADDRESS


class TestTronServiceIncomingTransaction:
    """اختبارات المعاملات الواردة"""
    
    @patch('src.services.tron.TronService._make_request')
    @patch('src.services.tron.TronService._get_transaction_confirmations')
    def test_check_incoming_transaction_found(self, mock_confirmations, mock_request):
        mock_request.return_value = {
            "data": [
                {
                    "transaction_id": "tx_hash_123",
                    "tokenId": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                    "value": "100000000",  # 100 USDT
                    "from": "TSenderAddress123",
                    "to": "TReceiverAddress456",
                    "memo": "deal_123",
                    "blockNumber": 50000000,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ]
        }
        mock_confirmations.return_value = 25
        
        service = TronService()
        result = service.check_incoming_transaction(
            "TReceiverAddress456",
            Decimal("100"),
            memo="deal_123"
        )
        
        assert result is not None
        assert result.tx_hash == "tx_hash_123"
        assert result.amount == Decimal("100")
        assert result.is_confirmed is True
        assert result.confirmations == 25
        assert result.is_sufficient is True
    
    @patch('src.services.tron.TronService._make_request')
    def test_check_incoming_transaction_not_found(self, mock_request):
        mock_request.return_value = {"data": []}
        
        service = TronService()
        result = service.check_incoming_transaction(
            "TReceiverAddress456",
            Decimal("100")
        )
        
        assert result is None
    
    @patch('src.services.tron.TronService._make_request')
    @patch('src.services.tron.TronService._get_transaction_confirmations')
    def test_check_incoming_transaction_insufficient_confirmations(self, mock_confirmations, mock_request):
        mock_request.return_value = {
            "data": [
                {
                    "transaction_id": "tx_hash_123",
                    "tokenId": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                    "value": "100000000",
                    "from": "TSenderAddress123",
                    "to": "TReceiverAddress456",
                    "blockNumber": 50000000
                }
            ]
        }
        mock_confirmations.return_value = 5  # أقل من MIN_CONFIRMATIONS (20)
        
        service = TronService()
        result = service.check_incoming_transaction(
            "TReceiverAddress456",
            Decimal("100")
        )
        
        assert result is not None
        assert result.is_confirmed is False
        assert result.confirmations == 5


class TestTronServicePayout:
    """اختبارات إرسال المدفوعات"""
    
    def test_send_payout_no_private_key(self):
        service = TronService()
        result = service.send_payout(
            "TReceiverAddress456",
            Decimal("100"),
            "idempotency_123"
        )
        
        assert result.success is False
        assert result.error == "Private key not configured"
    
    @patch('src.services.tron.TronService.get_wallet_balance')
    def test_send_payout_insufficient_balance(self, mock_balance):
        mock_balance.return_value = Decimal("50")
        
        service = TronService()
        service._private_key = "test_key"
        
        with pytest.raises(InsufficientFundsError):
            service.send_payout(
                "TReceiverAddress456",
                Decimal("100"),
                "idempotency_123"
            )
    
    def test_send_payout_invalid_address(self):
        service = TronService()
        service._private_key = "test_key"
        service.get_wallet_balance = MagicMock(return_value=Decimal("200"))
        service.get_trx_balance = MagicMock(return_value=Decimal("100"))
        service.estimate_energy = MagicMock(return_value=EnergyEstimation(
            energy_needed=13000, energy_price_sun=420,
            bandwidth_needed=250, bandwidth_price_sun=1000,
            total_fee_sun=1000000, total_fee_trx=Decimal("1"),
            is_new_address=False
        ))
        
        with pytest.raises(InvalidAddressError):
            service.send_payout(
                "invalid_address",
                Decimal("100"),
                "idempotency_123"
            )


class TestTronServiceHealthCheck:
    """اختبارات فحص الصحة"""
    
    @patch('src.services.tron.TronService._make_request')
    @patch('src.services.tron.TronService.get_wallet_balance')
    def test_health_check_healthy(self, mock_balance, mock_request):
        mock_request.return_value = {"number": 50000000}
        mock_balance.return_value = Decimal("1000")
        
        service = TronService()
        health = service.health_check()
        
        assert health.status == "healthy"
        assert health.api_connected is True
        assert health.wallet_balance == 1000.0
    
    @patch('src.services.tron.TronService._make_request')
    @patch('src.services.tron.TronService.get_wallet_balance')
    def test_health_check_degraded_low_balance(self, mock_balance, mock_request):
        mock_request.return_value = {"number": 50000000}
        mock_balance.return_value = Decimal("50")  # أقل من 100
        
        service = TronService()
        health = service.health_check()
        
        assert health.status == "degraded"
    
    @patch('src.services.tron.TronService._make_request')
    def test_health_check_unhealthy(self, mock_request):
        mock_request.side_effect = Exception("API down")
        
        service = TronService()
        health = service.health_check()
        
        assert health.status == "unhealthy"
        assert health.api_connected is False


class TestTronServiceMetrics:
    """اختبارات الإحصائيات"""
    
    def test_get_metrics(self):
        service = TronService(network=TronNetwork.SHASTA)
        metrics = service.get_metrics()
        
        assert "network" in metrics
        assert metrics["network"] == TronNetwork.SHASTA
        assert "circuit_breaker" in metrics
        assert "pending_transactions" in metrics
        assert "wallet_balance" in metrics
        assert "trx_balance" in metrics
    
    def test_test_connection_success(self):
        service = TronService()
        service._make_request = MagicMock(return_value={"number": 50000000})
        
        assert service.test_connection() is True
    
    def test_test_connection_failure(self):
        service = TronService()
        service._make_request = MagicMock(side_effect=Exception("Failed"))
        
        assert service.test_connection() is False


class TestTronServiceCircuitBreakerIntegration:
    """اختبارات تكامل Circuit Breaker"""
    
    def test_circuit_breaker_opens_after_failures(self):
        cb = CircuitBreaker(name="test_tron", failure_threshold=2, timeout=0.1)
        service = TronService(circuit_breaker=cb)
        
        service._make_request = MagicMock(side_effect=Exception("API Error"))
        
        for _ in range(2):
            with pytest.raises(Exception):
                service.test_connection()
        
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_circuit_breaker_used_for_requests(self):
        service = TronService()
        service._make_request = MagicMock(return_value={"data": []})
        
        result = service.check_incoming_transaction("TAddress", Decimal("100"))
        
        assert result is None
        assert service.circuit_breaker.get_metrics()["total_success"] >= 1


class TestTronServiceEdgeCases:
    """اختبارات حالات خاصة"""
    
    def test_private_key_decryption(self):
        from src.app.models.security import encrypt_data
        
        original_key = "a" * 64
        encrypted = encrypt_data(original_key)
        
        service = TronService(
            encrypted_private_key=encrypted,
            encryption_key="test_key"
        )
        # المفتاح الخاص تم فك تشفيره
        assert service._private_key is not None
    
    def test_custom_usdt_contract(self):
        custom_contract = "TCustomContractAddress123"
        service = TronService(usdt_contract=custom_contract)
        assert service.usdt_contract == custom_contract
    
    def test_custom_min_confirmations(self):
        service = TronService(min_confirmations=30)
        assert service.min_confirmations == 30


__all__ = [
    "TestTronServiceBasic",
    "TestTronServiceBalance",
    "TestTronServicePaymentAddress",
    "TestTronServiceEnergyEstimation",
    "TestTronServiceIncomingTransaction",
    "TestTronServicePayout",
    "TestTronServiceHealthCheck",
    "TestTronServiceMetrics",
    "TestTronServiceCircuitBreakerIntegration",
    "TestTronServiceEdgeCases",
]

"""
اختبارات محرك الوساطة المالية
Unit Tests for Escrow Engine
"""

import sys
import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.escrow import (
    EscrowEngine,
    EscrowEvent,
    PayoutStatus,
    FeeCalculation,
    PaymentVerificationResult,
    EscrowPayoutResult,
    ReconciliationReport,
    HealthStatus,
)
from src.services.tron import (
    PayoutResult,
    TransactionVerification,
    HealthStatus as TronHealthStatus,
)
from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerState


class MockDeal:
    """محاكاة الصفقة"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'deal_123')
        self.title = kwargs.get('title', 'Test Deal')
        self.amount = kwargs.get('amount', Decimal('1000'))
        self.status = kwargs.get('status', 'pending')
        self.buyer_id = kwargs.get('buyer_id', 'buyer_123')
        self.seller_id = kwargs.get('seller_id', 'seller_456')
        self.escrow_address = kwargs.get('escrow_address', 'TTestAddress123')
        self.payment_memo = kwargs.get('payment_memo', 'memo_123')
        self.payout_details = kwargs.get('payout_details', {'address': 'TSellerAddress456'})
        self.delivered_at = kwargs.get('delivered_at', None)
        self.escrow_tx_hash = kwargs.get('escrow_tx_hash', None)
        self.release_tx_id = kwargs.get('release_tx_id', None)
        self.payout_status = kwargs.get('payout_status', None)
    
    def fund(self, buyer_id, tx_hash):
        self.status = 'funded'
        self.escrow_tx_hash = tx_hash
    
    def complete(self, tx_hash):
        self.status = 'completed'
        self.release_tx_id = tx_hash
    
    def cancel(self, reason, cancelled_by):
        self.status = 'cancelled'


class TestFeeCalculation:
    """اختبارات حساب الرسوم"""
    
    def test_calculate_fee_default(self):
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock(),
            platform_fee_percent=Decimal('1.0')
        )
        
        fee = engine.calculate_fee(Decimal('1000'))
        assert fee.amount == Decimal('1000')
        assert fee.platform_fee == Decimal('10')
        assert fee.seller_amount == Decimal('990')
    
    def test_calculate_fee_with_discount(self):
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock(),
            platform_fee_percent=Decimal('2.0')
        )
        
        # محاكاة مستخدم ذو تقييم عالي
        user = MagicMock()
        user.rating = 4.8
        
        fee = engine.calculate_fee(Decimal('1000'), user)
        assert fee.fee_percent < Decimal('2.0')  # خصم 20%
    
    def test_calculate_fee_large_amount(self):
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock(),
            platform_fee_percent=Decimal('1.0')
        )
        
        fee = engine.calculate_fee(Decimal('20000'))  # مبلغ كبير
        assert fee.fee_percent < Decimal('1.0')  # خصم 10%


class TestPaymentVerification:
    """اختبارات التحقق من الدفع"""
    
    def test_verify_payment_success(self):
        mock_tron = MagicMock()
        mock_tron.check_incoming_transaction.return_value = TransactionVerification(
            tx_hash='tx_123',
            amount=Decimal('1000'),
            from_address='TBuyer',
            to_address='TEscrow',
            confirmations=25,
            is_confirmed=True,
            is_sufficient=True,
            expected_amount=Decimal('1000'),
            block_number=50000000,
            timestamp='2024-01-01T00:00:00Z'
        )
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=MagicMock()
        )
        
        deal = MockDeal(amount=Decimal('1000'))
        result = engine.verify_payment(deal)
        
        assert result.verified is True
        assert result.tx_hash == 'tx_123'
        assert result.amount == Decimal('1000')
    
    def test_verify_payment_not_found(self):
        mock_tron = MagicMock()
        mock_tron.check_incoming_transaction.return_value = None
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=MagicMock()
        )
        
        deal = MockDeal()
        result = engine.verify_payment(deal)
        
        assert result.verified is False
        assert result.error == 'No transaction found'
    
    def test_verify_payment_insufficient(self):
        mock_tron = MagicMock()
        mock_tron.check_incoming_transaction.return_value = TransactionVerification(
            tx_hash='tx_123',
            amount=Decimal('500'),
            from_address='TBuyer',
            to_address='TEscrow',
            confirmations=25,
            is_confirmed=True,
            is_sufficient=False,
            expected_amount=Decimal('1000'),
            block_number=50000000,
            timestamp=''
        )
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=MagicMock()
        )
        
        deal = MockDeal(amount=Decimal('1000'))
        result = engine.verify_payment(deal)
        
        assert result.verified is False
        assert 'Insufficient amount' in result.error
    
    def test_verify_payment_not_confirmed(self):
        mock_tron = MagicMock()
        mock_tron.check_incoming_transaction.return_value = TransactionVerification(
            tx_hash='tx_123',
            amount=Decimal('1000'),
            from_address='TBuyer',
            to_address='TEscrow',
            confirmations=5,
            is_confirmed=False,
            is_sufficient=True,
            expected_amount=Decimal('1000'),
            block_number=50000000,
            timestamp=''
        )
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=MagicMock()
        )
        
        deal = MockDeal(amount=Decimal('1000'))
        result = engine.verify_payment(deal)
        
        assert result.verified is False
        assert 'Not enough confirmations' in result.error
    
    def test_mark_as_funded(self):
        mock_repo = MagicMock()
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=mock_repo,
            notification_service=MagicMock()
        )
        
        deal = MockDeal()
        result = engine.mark_as_funded(deal, 'tx_123')
        
        assert result is True
        assert deal.status == 'funded'
        assert deal.escrow_tx_hash == 'tx_123'
        mock_repo.update.assert_called_once()


class TestPayoutProcessing:
    """اختبارات معالجة المدفوعات"""
    
    def test_process_payout_success(self):
        mock_tron = MagicMock()
        mock_tron.send_payout.return_value = PayoutResult(
            success=True,
            tx_hash='payout_tx_123',
            amount=Decimal('990'),
            to_address='TSeller',
            fee_trx=Decimal('1'),
            idempotency_key='key_123'
        )
        
        mock_repo = MagicMock()
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=mock_repo,
            notification_service=MagicMock()
        )
        
        deal = MockDeal(status='delivered', amount=Decimal('1000'))
        result = engine.process_payout(deal, 'key_123')
        
        assert result.success is True
        assert result.tx_hash == 'payout_tx_123'
        assert result.status == PayoutStatus.SENT
        assert deal.status == 'completed'
    
    def test_process_payout_not_ready(self):
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock()
        )
        
        deal = MockDeal(status='pending')
        result = engine.process_payout(deal, 'key_123')
        
        assert result.success is False
        assert 'not ready' in result.error
    
    def test_process_payout_tron_failure(self):
        mock_tron = MagicMock()
        mock_tron.send_payout.return_value = PayoutResult(
            success=False,
            tx_hash=None,
            amount=Decimal('990'),
            to_address='TSeller',
            fee_trx=Decimal('0'),
            idempotency_key='key_123',
            error='Network error'
        )
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=MagicMock()
        )
        
        deal = MockDeal(status='delivered', amount=Decimal('1000'))
        result = engine.process_payout(deal, 'key_123')
        
        assert result.success is False
        assert result.error == 'Network error'


class TestAutoRelease:
    """اختبارات التحرير التلقائي"""
    
    def test_release_funds_auto_ready(self):
        from datetime import timedelta
        from src.app.models.helpers import utc_now
        
        mock_tron = MagicMock()
        mock_tron.send_payout.return_value = PayoutResult(
            success=True,
            tx_hash='auto_tx_123',
            amount=Decimal('990'),
            to_address='TSeller',
            fee_trx=Decimal('1'),
            idempotency_key='auto_key'
        )
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=MagicMock(),
            notification_service=MagicMock()
        )
        
        deal = MockDeal(status='delivered', amount=Decimal('1000'))
        deal.delivered_at = utc_now() - timedelta(hours=50)
        
        result = engine.release_funds_auto(deal)
        assert result is True
        assert deal.status == 'completed'
    
    def test_release_funds_auto_not_ready(self):
        from datetime import timedelta
        from src.app.models.helpers import utc_now
        
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock()
        )
        
        deal = MockDeal(status='delivered')
        deal.delivered_at = utc_now() - timedelta(hours=1)
        
        result = engine.release_funds_auto(deal)
        assert result is False
    
    def test_release_funds_auto_wrong_status(self):
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock()
        )
        
        deal = MockDeal(status='pending')
        result = engine.release_funds_auto(deal)
        assert result is False


class TestExpiredAndStalled:
    """اختبارات الصفقات المنتهية والمتوقفة"""
    
    def test_process_expired_deals(self):
        deal = MockDeal(status='pending')
        
        mock_repo = MagicMock()
        mock_repo.get_expired_deals.return_value = [deal]
        
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=mock_repo,
            notification_service=MagicMock()
        )
        
        count = engine.process_expired_deals()
        assert count == 1
        assert deal.status == 'cancelled'
    
    def test_process_stalled_deals(self):
        deal1 = MockDeal(id='deal1', status='funded')
        deal2 = MockDeal(id='deal2', status='in_progress')
        
        mock_repo = MagicMock()
        mock_repo.get_stalled.return_value = [deal1, deal2]
        
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=mock_repo,
            notification_service=MagicMock()
        )
        
        stalled = engine.process_stalled_deals()
        assert len(stalled) == 2


class TestReconciliation:
    """اختبارات المطابقة"""
    
    def test_reconcile_transactions(self):
        deal = MockDeal(amount=Decimal('1000'))
        deal.escrow_tx_hash = 'tx_123'
        deal.status = 'completed'
        
        mock_repo = MagicMock()
        mock_repo.get_completed_today.return_value = [deal]
        
        mock_tron = MagicMock()
        mock_tron.verify_transaction.return_value = TransactionVerification(
            tx_hash='tx_123',
            amount=Decimal('1000'),
            from_address='TBuyer',
            to_address='TEscrow',
            confirmations=30,
            is_confirmed=True,
            is_sufficient=True,
            expected_amount=Decimal('1000'),
            block_number=50000000,
            timestamp=''
        )
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=mock_repo
        )
        
        report = engine.reconcile_transactions()
        assert report.total == 1
        assert report.matched == 1
        assert report.mismatched == 0
    
    def test_reconcile_transactions_mismatch(self):
        deal = MockDeal(amount=Decimal('1000'))
        deal.escrow_tx_hash = 'tx_123'
        deal.status = 'completed'
        
        mock_repo = MagicMock()
        mock_repo.get_completed_today.return_value = [deal]
        
        mock_tron = MagicMock()
        mock_tron.verify_transaction.return_value = TransactionVerification(
            tx_hash='tx_123',
            amount=Decimal('900'),  # مبلغ مختلف
            from_address='TBuyer',
            to_address='TEscrow',
            confirmations=30,
            is_confirmed=True,
            is_sufficient=True,
            expected_amount=Decimal('1000'),
            block_number=50000000,
            timestamp=''
        )
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=mock_repo
        )
        
        report = engine.reconcile_transactions()
        assert report.total == 1
        assert report.matched == 0
        assert report.mismatched == 1
        assert len(report.mismatches) == 1


class TestHealthCheck:
    """اختبارات فحص الصحة"""
    
    def test_health_check_healthy(self):
        mock_tron = MagicMock()
        mock_tron.health_check.return_value = TronHealthStatus(
            status='healthy',
            network='mainnet',
            api_connected=True,
            wallet_balance=1000.0,
            current_node='https://api.trongrid.io',
            circuit_breaker_state='closed',
            pending_transactions=0
        )
        
        mock_repo = MagicMock()
        mock_repo.get_stalled.return_value = []
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=mock_repo
        )
        
        health = engine.health_check()
        assert health.status == 'healthy'
        assert health.tron_status == 'healthy'
    
    def test_health_check_degraded(self):
        mock_tron = MagicMock()
        mock_tron.health_check.return_value = TronHealthStatus(
            status='degraded',
            network='mainnet',
            api_connected=True,
            wallet_balance=50.0,
            current_node='https://api.trongrid.io',
            circuit_breaker_state='closed',
            pending_transactions=0
        )
        
        mock_repo = MagicMock()
        mock_repo.get_stalled.return_value = []
        
        engine = EscrowEngine(
            tron_service=mock_tron,
            deal_repository=mock_repo
        )
        
        health = engine.health_check()
        assert health.status == 'degraded'
    
    def test_get_metrics(self):
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock()
        )
        
        metrics = engine.get_metrics()
        assert 'platform_fee_percent' in metrics
        assert 'pending_payouts' in metrics
        assert 'circuit_breaker' in metrics
        assert 'tron_metrics' in metrics


class TestManualPayout:
    """اختبارات المدفوعات اليدوية"""
    
    def test_create_manual_payout_task(self):
        engine = EscrowEngine(
            tron_service=MagicMock(),
            deal_repository=MagicMock()
        )
        
        deal = MockDeal()
        task_id = engine.create_manual_payout_task(deal)
        
        assert task_id.startswith('manual_payout_')
        assert task_id in engine._pending_payouts
        assert engine._pending_payouts[task_id]['deal_id'] == 'deal_123'


__all__ = [
    "TestFeeCalculation",
    "TestPaymentVerification",
    "TestPayoutProcessing",
    "TestAutoRelease",
    "TestExpiredAndStalled",
    "TestReconciliation",
    "TestHealthCheck",
    "TestManualPayout",
]

"""
اختبارات نموذج المعاملات
Unit Tests for Transaction Model
"""

import sys
import os
import tempfile
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.transaction import (
    Transaction,
    TransactionType,
    TransactionStatus,
    TransactionNetwork,
)
from src.app.models.helpers import utc_now


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
def test_user(db_session):
    user = User(email="tx_test@ex.com", username="txuser")
    user.set_password("Test123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_transaction(db_session, test_user):
    tx = Transaction(
        transaction_uuid="tx-uuid-123",
        user_id=str(test_user.id),
        tx_type=TransactionType.ESCROW_DEPOSIT,
        amount_usdt=Decimal("1000.00"),
        from_address="TFromAddress123456789",
        to_address="TToAddress123456789"
    )
    db_session.add(tx)
    db_session.commit()
    return tx


class TestTransactionBasic:
    """اختبارات أساسية"""
    
    def test_create_transaction(self, db_session, test_user):
        tx = Transaction(
            transaction_uuid="tx-uuid-456",
            user_id=str(test_user.id),
            tx_type=TransactionType.PAYOUT,
            amount_usdt=Decimal("500.00")
        )
        db_session.add(tx)
        db_session.commit()
        
        assert tx.id is not None
        assert tx.transaction_uuid == "tx-uuid-456"
        assert tx.tx_type == TransactionType.PAYOUT
        assert tx.amount_usdt == Decimal("500.00")
        assert tx.status == TransactionStatus.PENDING
        assert tx.retry_count == 0
    
    def test_transaction_unique_uuid(self, db_session, test_user):
        tx1 = Transaction(
            transaction_uuid="tx-uuid-789",
            user_id=str(test_user.id),
            tx_type=TransactionType.ESCROW_DEPOSIT,
            amount_usdt=Decimal("100.00")
        )
        db_session.add(tx1)
        db_session.commit()
        
        tx2 = Transaction(
            transaction_uuid="tx-uuid-789",
            user_id=str(test_user.id),
            tx_type=TransactionType.ESCROW_DEPOSIT,
            amount_usdt=Decimal("100.00")
        )
        db_session.add(tx2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestTransactionProperties:
    """اختبارات الخصائص"""
    
    def test_is_confirmed(self, test_transaction):
        assert test_transaction.is_confirmed is False
        test_transaction.status = TransactionStatus.CONFIRMED
        assert test_transaction.is_confirmed is True
    
    def test_is_pending(self, test_transaction):
        assert test_transaction.is_pending is True
        test_transaction.status = TransactionStatus.CONFIRMED
        assert test_transaction.is_pending is False
    
    def test_is_failed(self, test_transaction):
        assert test_transaction.is_failed is False
        test_transaction.mark_failed("Test error")
        assert test_transaction.is_failed is True
    
    def test_has_sufficient_confirmations(self, test_transaction):
        test_transaction.block_confirmations = 5
        assert test_transaction.has_sufficient_confirmations is False
        test_transaction.block_confirmations = 25
        assert test_transaction.has_sufficient_confirmations is True
    
    def test_masked_addresses(self, test_transaction):
        assert test_transaction.masked_from_address == "TFromA...6789"
        assert test_transaction.masked_to_address == "TToAdd...6789"
    
    def test_explorer_url(self, test_transaction):
        test_transaction.tx_hash = "abc123"
        test_transaction.network = TransactionNetwork.TRON_MAINNET
        assert "tronscan.org" in test_transaction.explorer_url
        assert "abc123" in test_transaction.explorer_url
    
    def test_next_retry_delay(self, test_transaction):
        assert test_transaction.next_retry_delay == 1
        test_transaction.retry_count = 2
        assert test_transaction.next_retry_delay == 4


class TestTransactionMethods:
    """اختبارات الدوال"""
    
    def test_confirm(self, test_transaction):
        test_transaction.confirm(50000000)
        assert test_transaction.status == TransactionStatus.CONFIRMED
        assert test_transaction.confirmed_at is not None
        assert test_transaction.block_number == 50000000
    
    def test_update_confirmations(self, test_transaction):
        test_transaction.block_number = 50000000
        test_transaction.update_confirmations(50000015)
        assert test_transaction.block_confirmations == 15
    
    def test_update_confirmations_auto_confirm(self, test_transaction):
        test_transaction.block_number = 50000000
        test_transaction.status = TransactionStatus.PENDING
        test_transaction.update_confirmations(50000025)
        assert test_transaction.status == TransactionStatus.CONFIRMED
        assert test_transaction.block_confirmations == 25
    
    def test_mark_processing(self, test_transaction):
        test_transaction.mark_processing()
        assert test_transaction.status == TransactionStatus.PROCESSING
    
    def test_mark_failed(self, test_transaction):
        test_transaction.mark_failed("Network error")
        assert test_transaction.status == TransactionStatus.FAILED
        assert test_transaction.error_message == "Network error"
    
    def test_mark_cancelled(self, test_transaction):
        test_transaction.mark_cancelled("User requested")
        assert test_transaction.status == TransactionStatus.CANCELLED
        assert test_transaction.error_message == "User requested"
    
    def test_mark_retrying(self, test_transaction):
        test_transaction.status = TransactionStatus.FAILED
        result = test_transaction.mark_retrying()
        assert result is True
        assert test_transaction.status == TransactionStatus.RETRYING
        assert test_transaction.retry_count == 1
        assert test_transaction.last_retry_at is not None
    
    def test_can_retry(self, test_transaction):
        test_transaction.status = TransactionStatus.FAILED
        assert test_transaction.can_retry() is True
        
        test_transaction.retry_count = 3
        assert test_transaction.can_retry() is False
    
    def test_calculate_total(self, test_transaction):
        test_transaction.amount_usdt = Decimal("100.00")
        test_transaction.amount_trx = Decimal("10.00")
        test_transaction.fee_trx = Decimal("1.00")
        assert test_transaction.calculate_total() == Decimal("111.00")


class TestTransactionIdempotency:
    """اختبارات Idempotency"""
    
    def test_find_by_idempotency(self, db_session, test_transaction):
        found = Transaction.find_by_idempotency(db_session, "tx-uuid-123")
        assert found is not None
        assert found.id == test_transaction.id
        
        not_found = Transaction.find_by_idempotency(db_session, "non-existent")
        assert not_found is None
    
    def test_create_with_idempotency_new(self, db_session, test_user):
        tx, created = Transaction.create_with_idempotency(
            db_session,
            "new-idempotency-key",
            user_id=str(test_user.id),
            tx_type=TransactionType.PAYOUT,
            amount_usdt=Decimal("200.00")
        )
        db_session.commit()
        
        assert created is True
        assert tx.id is not None
        assert tx.transaction_uuid == "new-idempotency-key"
    
    def test_create_with_idempotency_existing(self, db_session, test_transaction):
        tx, created = Transaction.create_with_idempotency(
            db_session,
            "tx-uuid-123",
            user_id=str(test_transaction.user_id),
            tx_type=TransactionType.PAYOUT,
            amount_usdt=Decimal("200.00")
        )
        
        assert created is False
        assert tx.id == test_transaction.id
        assert tx.tx_type == TransactionType.ESCROW_DEPOSIT  # القيمة الأصلية


class TestTransactionStats:
    """اختبارات الإحصائيات"""
    
    def test_get_stats(self, db_session, test_user):
        tx1 = Transaction(
            transaction_uuid="stats-1",
            user_id=str(test_user.id),
            tx_type=TransactionType.ESCROW_DEPOSIT,
            amount_usdt=Decimal("100.00"),
            status=TransactionStatus.CONFIRMED
        )
        tx2 = Transaction(
            transaction_uuid="stats-2",
            user_id=str(test_user.id),
            tx_type=TransactionType.PAYOUT,
            amount_usdt=Decimal("50.00"),
            status=TransactionStatus.FAILED
        )
        db_session.add_all([tx1, tx2])
        db_session.commit()
        
        stats = Transaction.get_stats(db_session, user_id=str(test_user.id))
        assert stats['total'] >= 2
        assert stats['confirmed'] >= 1
        assert stats['failed'] >= 1
        assert stats['total_usdt'] >= 150.0


class TestTransactionSerialization:
    """اختبارات التحويل"""
    
    def test_to_dict(self, test_transaction):
        data = test_transaction.to_dict()
        assert data['id'] == str(test_transaction.id)
        assert data['transaction_uuid'] == "tx-uuid-123"
        assert data['tx_type'] == TransactionType.ESCROW_DEPOSIT
        assert data['amount_usdt'] == 1000.0
        assert 'error_message' not in data  # ليس في الوضع العادي
    
    def test_to_dict_include_sensitive(self, test_transaction):
        test_transaction.error_message = "Test error"
        data = test_transaction.to_dict(include_sensitive=True)
        assert data['error_message'] == "Test error"
        assert data['from_address'] == "TFromAddress123456789"


__all__ = [
    "TestTransactionBasic",
    "TestTransactionProperties",
    "TestTransactionMethods",
    "TestTransactionIdempotency",
    "TestTransactionStats",
    "TestTransactionSerialization",
]

"""
اختبارات نموذج النزاعات
Unit Tests for Dispute Model
"""

import sys
import os
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.deal import Deal, DealStatus
from src.app.models.dispute import (
    Dispute,
    DisputeStatus,
    DisputeReasonCategory,
    DisputeResolutionType,
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
def buyer(db_session):
    u = User(email="buyer@test.com", username="buyer")
    u.set_password("Test123!")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def seller(db_session):
    u = User(email="seller@test.com", username="seller")
    u.set_password("Test123!")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def deal(db_session, buyer, seller):
    d = Deal(
        title="Test Deal",
        seller_id=seller.id,
        buyer_id=buyer.id,
        amount=Decimal("1000.00"),
        status=DealStatus.FUNDED
    )
    db_session.add(d)
    db_session.commit()
    return d


@pytest.fixture
def dispute(db_session, deal, buyer):
    d = Dispute.open_dispute(
        db_session,
        deal.id,
        buyer.id,
        "Work quality is poor",
        DisputeReasonCategory.QUALITY
    )
    db_session.commit()
    return d


class TestDisputeBasic:
    def test_open_dispute(self, db_session, deal, buyer):
        dispute = Dispute.open_dispute(
            db_session,
            deal.id,
            buyer.id,
            "Test reason",
            DisputeReasonCategory.QUALITY
        )
        db_session.commit()
        
        assert dispute is not None
        assert dispute.id is not None
        assert dispute.dispute_uuid is not None
        assert dispute.status == DisputeStatus.OPENED
        assert dispute.deal_id == deal.id
        assert dispute.opened_by_id == buyer.id
    
    def test_cannot_open_duplicate_dispute(self, db_session, deal, buyer, dispute):
        can_open, msg = Dispute.can_open_dispute(db_session, deal.id, buyer.id)
        assert can_open is False
        assert "already exists" in msg
    
    def test_dispute_has_deadline(self, dispute):
        assert dispute.deadline is not None


class TestDisputeProperties:
    def test_is_active(self, dispute):
        assert dispute.is_active is True
        dispute.status = DisputeStatus.RESOLVED_BUYER
        assert dispute.is_active is False
    
    def test_is_resolved(self, dispute):
        assert dispute.is_resolved is False
        dispute.resolve("Refund", DisputeResolutionType.FULL_REFUND, uuid.uuid4())
        assert dispute.is_resolved is True


class TestDisputeMethods:
    def test_add_evidence(self, dispute):
        evidence_id = dispute.add_evidence("image", "url", "desc", str(uuid.uuid4()))
        assert len(dispute.evidence) == 1
    
    def test_remove_evidence(self, dispute):
        evidence_id = dispute.add_evidence("image", "url", "desc")
        result = dispute.remove_evidence(evidence_id)
        assert result is True
    
    def test_resolve(self, dispute):
        admin_id = uuid.uuid4()
        dispute.resolve("Full refund", DisputeResolutionType.FULL_REFUND, admin_id)
        assert dispute.status == DisputeStatus.RESOLVED_BUYER
    
    def test_appeal(self, dispute):
        admin_id = uuid.uuid4()
        dispute.resolve("Test", DisputeResolutionType.FULL_REFUND, admin_id)
        result = dispute.appeal("I disagree")
        assert result is True
        assert dispute.status == DisputeStatus.APPEALED
    
    def test_close(self, dispute):
        dispute.close()
        assert dispute.status == DisputeStatus.CLOSED


class TestDisputeSerialization:
    def test_to_dict(self, dispute):
        data = dispute.to_dict()
        assert data['id'] == str(dispute.id)
        assert data['status'] == DisputeStatus.OPENED


__all__ = ["TestDisputeBasic", "TestDisputeProperties", "TestDisputeMethods", "TestDisputeSerialization"]

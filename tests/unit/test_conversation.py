"""
اختبارات نموذج المحادثة
"""

import sys, os, tempfile
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.conversation import Conversation, ConversationStatus


@pytest.fixture
def db_session():
    with tempfile.TemporaryDirectory() as tmp:
        engine = create_engine(f"sqlite:///{Path(tmp)/'test.db'}")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        s = Session()
        yield s
        s.close()


@pytest.fixture
def buyer(db_session):
    u = User(email="b@t.com", username="buyer")
    u.set_password("pass")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def seller(db_session):
    u = User(email="s@t.com", username="seller")
    u.set_password("pass")
    db_session.add(u)
    db_session.commit()
    return u


def test_create_conversation(db_session, buyer, seller):
    c = Conversation(
        deal_id="deal-123",
        buyer_id=str(buyer.id),
        seller_id=str(seller.id),
        subject="Test"
    )
    db_session.add(c)
    db_session.commit()
    
    assert c.id is not None
    assert c.status == ConversationStatus.ACTIVE
    assert c.is_deleted is False
    assert c.is_participant(str(buyer.id)) is True
    assert c.is_participant(str(seller.id)) is True


def test_soft_delete_restore(db_session, buyer, seller):
    c = Conversation(
        buyer_id=str(buyer.id),
        seller_id=str(seller.id)
    )
    db_session.add(c)
    db_session.commit()
    
    c.soft_delete()
    assert c.is_deleted is True
    assert c.status == ConversationStatus.DELETED
    
    c.restore()
    assert c.is_deleted is False
    assert c.status == ConversationStatus.ACTIVE


def test_get_other_participant(db_session, buyer, seller):
    c = Conversation(
        buyer_id=str(buyer.id),
        seller_id=str(seller.id)
    )
    db_session.add(c)
    db_session.commit()
    
    assert c.get_other_participant(str(buyer.id)) == str(seller.id)
    assert c.get_other_participant(str(seller.id)) == str(buyer.id)


def test_update_last_message(db_session, buyer, seller):
    c = Conversation(
        buyer_id=str(buyer.id),
        seller_id=str(seller.id)
    )
    db_session.add(c)
    db_session.commit()
    
    c.update_last_message()
    assert c.last_message_at is not None


def test_to_dict(db_session, buyer, seller):
    c = Conversation(
        deal_id="deal-123",
        buyer_id=str(buyer.id),
        seller_id=str(seller.id),
        subject="Test Subject"
    )
    db_session.add(c)
    db_session.commit()
    
    d = c.to_dict()
    assert d["id"] == str(c.id)
    assert d["deal_id"] == "deal-123"
    assert d["subject"] == "Test Subject"
    assert d["status"] == ConversationStatus.ACTIVE

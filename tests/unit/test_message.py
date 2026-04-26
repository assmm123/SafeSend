"""
اختبارات نموذج الرسائل
"""

import sys, os, tempfile
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.conversation import Conversation
from src.app.models.message import Message, MessageType, DeliveryStatus


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
def sender(db_session):
    u = User(email="s@t.com", username="sender")
    u.set_password("pass")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def receiver(db_session):
    u = User(email="r@t.com", username="receiver")
    u.set_password("pass")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def conv(db_session, sender, receiver):
    c = Conversation(buyer_id=str(sender.id), seller_id=str(receiver.id))
    db_session.add(c)
    db_session.commit()
    return c


def test_create_message(db_session, conv, sender):
    m = Message(conversation_id=str(conv.id), sender_id=str(sender.id), content="Hello")
    db_session.add(m)
    db_session.commit()
    assert m.id is not None
    assert m.content == "Hello"
    assert m.is_read is False
    assert m.delivery_status == DeliveryStatus.SENT


def test_mark_as_read(db_session, conv, sender):
    m = Message(conversation_id=str(conv.id), sender_id=str(sender.id), content="Hi")
    db_session.add(m)
    db_session.commit()
    m.mark_as_read()
    assert m.is_read is True
    assert m.read_at is not None


def test_edit_message(db_session, conv, sender):
    m = Message(conversation_id=str(conv.id), sender_id=str(sender.id), content="Old")
    db_session.add(m)
    db_session.commit()
    m.edit("New")
    assert m.content == "New"
    assert m.is_edited is True


def test_soft_delete(db_session, conv, sender):
    m = Message(conversation_id=str(conv.id), sender_id=str(sender.id), content="Delete me")
    db_session.add(m)
    db_session.commit()
    m.soft_delete()
    assert m.is_deleted is True


def test_reactions(db_session, conv, sender):
    m = Message(conversation_id=str(conv.id), sender_id=str(sender.id), content="React")
    db_session.add(m)
    db_session.commit()
    m.add_reaction("user1", "👍")
    assert m.reactions["👍"] == ["user1"]


def test_get_unread_count(db_session, conv, sender, receiver):
    m1 = Message(conversation_id=str(conv.id), sender_id=str(receiver.id), content="Unread")
    m2 = Message(conversation_id=str(conv.id), sender_id=str(sender.id), content="Read", is_read=True)
    db_session.add_all([m1, m2])
    db_session.commit()
    count = Message.get_unread_count(db_session, str(conv.id), str(sender.id))
    assert count == 1


def test_to_dict(db_session, conv, sender):
    m = Message(conversation_id=str(conv.id), sender_id=str(sender.id), content="Dict")
    db_session.add(m)
    db_session.commit()
    d = m.to_dict()
    assert d["content"] == "Dict"

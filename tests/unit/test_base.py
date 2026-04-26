"""
اختبارات الصنف الأساسي BaseModel
Unit Tests for BaseModel Class
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base, BaseModel


class TestModel(BaseModel):
    __tablename__ = "test_model"
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_id_is_uuid(db_session):
    model = TestModel(name="test")
    model.save(db_session)
    db_session.commit()
    assert isinstance(model.id, uuid.UUID)


def test_created_at_is_datetime(db_session):
    model = TestModel(name="test")
    model.save(db_session)
    db_session.commit()
    assert isinstance(model.created_at, datetime)


def test_to_dict(db_session):
    model = TestModel(name="test_dict")
    model.save(db_session)
    db_session.commit()
    result = model.to_dict()
    assert result["name"] == "test_dict"


def test_save(db_session):
    model = TestModel(name="save_test")
    model.save(db_session)
    assert model in db_session.new
    db_session.rollback()


def test_delete(db_session):
    model = TestModel(name="delete_test")
    model.save(db_session)
    db_session.commit()
    model.delete(db_session)
    db_session.commit()
    result = db_session.get(TestModel, model.id)
    assert result is None


def test_update(db_session):
    model = TestModel(name="old_name")
    model.save(db_session)
    db_session.commit()
    model.update(db_session, name="new_name")
    db_session.commit()
    assert model.name == "new_name"


def test_repr(db_session):
    model = TestModel(name="repr_test")
    model.save(db_session)
    db_session.commit()
    assert repr(model).startswith("<TestModel")


__all__ = ["TestModel"]

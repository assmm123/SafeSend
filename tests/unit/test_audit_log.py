"""
اختبارات نموذج سجل التدقيق
"""

import sys, os, tempfile
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.audit_log import AuditLog, AuditLogger, AuditAction, AuditSeverity, AuditResource, sanitize_data


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
def test_user(db_session):
    u = User(email="test@example.com", username="testuser")
    u.set_password("pass123")
    db_session.add(u)
    db_session.commit()
    return u


class TestSanitizeData:
    def test_none(self): assert sanitize_data(None) is None
    def test_string(self): assert sanitize_data("hello") == "hello"
    def test_long_string(self): assert "..." in sanitize_data("a" * 200)
    def test_sensitive_dict(self):
        assert sanitize_data({"password": "secret"})["password"] == "***REDACTED***"
    def test_nested_dict(self):
        assert sanitize_data({"user": {"password": "x"}})["user"]["password"] == "***REDACTED***"
    def test_list_truncation(self):
        assert "..." in sanitize_data(list(range(15)))


class TestAuditLog:
    def test_create(self, db_session, test_user):
        log = AuditLogger.log(db_session, AuditAction.CREATE, AuditResource.USER, str(test_user.id))
        assert log.id is not None
        assert log.action == AuditAction.CREATE
    
    def test_without_user(self, db_session):
        log = AuditLogger.log(db_session, AuditAction.VIEW, AuditResource.SYSTEM)
        assert log.user_id is None
    
    def test_sanitizes_password(self, db_session, test_user):
        log = AuditLogger.log(db_session, AuditAction.UPDATE, AuditResource.USER, str(test_user.id),
                              new_value={"password": "secret123"})
        assert log.new_value["password"] == "***REDACTED***"
    
    def test_get_for_user(self, db_session, test_user):
        AuditLogger.log(db_session, AuditAction.LOGIN, AuditResource.USER, str(test_user.id))
        logs = AuditLogger.get_for_user(db_session, str(test_user.id))
        assert len(logs) >= 1
    
    def test_get_for_resource(self, db_session, test_user):
        AuditLogger.log(db_session, AuditAction.UPDATE, AuditResource.USER, str(test_user.id), str(test_user.id))
        logs = AuditLogger.get_for_resource(db_session, AuditResource.USER, str(test_user.id))
        assert len(logs) >= 1


class TestAuditLogSeverity:
    def test_default(self, db_session, test_user):
        log = AuditLogger.log(db_session, AuditAction.VIEW, AuditResource.USER, str(test_user.id))
        assert log.severity == AuditSeverity.INFO
    
    def test_custom(self, db_session, test_user):
        log = AuditLogger.log(db_session, AuditAction.DELETE, AuditResource.USER, str(test_user.id),
                              severity=AuditSeverity.ERROR)
        assert log.severity == AuditSeverity.ERROR

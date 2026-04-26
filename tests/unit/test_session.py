"""
اختبارات نموذج الجلسات
Unit Tests for Session Model
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tempfile
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.session import (
    Session, SessionManager, DeviceType, SessionStatus,
    parse_user_agent, generate_device_fingerprint
)
from src.app.models.helpers import utc_now


@pytest.fixture
def db_session():
    """إنشاء جلسة قاعدة بيانات مؤقتة"""
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
    """إنشاء مستخدم اختباري"""
    user = User(
        email="session_test@example.com",
        username="sessionuser"
    )
    user.set_password("Test123!")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_session(db_session, test_user):
    """إنشاء جلسة اختبارية"""
    sess = SessionManager.create_session(
        db_session,
        user_id=str(test_user.id),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    )
    db_session.commit()
    return sess


class TestUserAgentParsing:
    """اختبارات تحليل User-Agent"""
    
    def test_parse_chrome_windows(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        info = parse_user_agent(ua)
        assert info['browser'] == 'Chrome'
        assert info['os'] == 'Windows'
        assert info['device'] == DeviceType.DESKTOP
    
    def test_parse_firefox(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/121.0"
        info = parse_user_agent(ua)
        assert info['browser'] == 'Firefox'
    
    def test_parse_mobile_android(self):
        ua = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile"
        info = parse_user_agent(ua)
        assert info['os'] == 'Android'
        assert info['device'] == DeviceType.MOBILE
        assert info['is_mobile'] is True
    
    def test_parse_iphone(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        info = parse_user_agent(ua)
        assert info['os'] == 'iOS'
        assert info['device'] == DeviceType.MOBILE
    
    def test_parse_bot(self):
        ua = "Googlebot/2.1 (+http://www.google.com/bot.html)"
        info = parse_user_agent(ua)
        assert info['is_bot'] is True
        assert info['device'] == DeviceType.BOT
    
    def test_parse_empty(self):
        info = parse_user_agent("")
        assert info['browser'] == 'Unknown'
        assert info['device'] == DeviceType.UNKNOWN


class TestSessionBasic:
    """اختبارات أساسية للجلسة"""
    
    def test_create_session(self, db_session, test_user):
        sess = SessionManager.create_session(
            db_session,
            user_id=str(test_user.id),
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0"
        )
        db_session.commit()
        
        assert sess.id is not None
        assert sess.user_id == str(test_user.id)
        assert sess.refresh_token is not None
        assert len(sess.refresh_token) == 64
        assert sess.is_active is True
        assert sess.status == SessionStatus.ACTIVE
    
    def test_session_has_device_info(self, test_session):
        assert test_session.device_info is not None
        assert 'browser' in test_session.device_info
        assert 'os' in test_session.device_info
    
    def test_session_has_fingerprint(self, test_session):
        assert test_session.device_fingerprint is not None
        assert len(test_session.device_fingerprint) == 32
    
    def test_session_expires_at_set(self, test_session):
        assert test_session.expires_at is not None
        assert test_session.expires_at.replace(tzinfo=None) >= utc_now().replace(tzinfo=None)


class TestSessionProperties:
    """اختبارات خصائص الجلسة"""
    
    def test_is_expired_false(self, test_session):
        assert test_session.is_expired is False
    
    def test_is_expired_true(self, db_session, test_user):
        sess = SessionManager.create_session(db_session, str(test_user.id))
        sess.expires_at = utc_now() - timedelta(days=1)
        db_session.commit()
        assert sess.is_expired is True
    
    def test_is_valid(self, test_session):
        assert test_session.is_valid is True
    
    def test_is_valid_when_revoked(self, test_session, db_session):
        test_session.revoke('test')
        db_session.commit()
        assert test_session.is_valid is False
        assert test_session.is_revoked is True
    
    def test_device_type_property(self, test_session):
        assert test_session.device_type in [DeviceType.DESKTOP, DeviceType.MOBILE, DeviceType.WEB]
    
    def test_browser_name_property(self, test_session):
        assert test_session.browser_name != 'Unknown'


class TestSessionTokens:
    """اختبارات التوكنات"""
    
    def test_generate_refresh_token(self, test_session):
        old_token = test_session.refresh_token
        new_token = test_session.generate_refresh_token()
        assert new_token != old_token
        assert len(new_token) == 64
    
    def test_verify_refresh_token_valid(self, test_session):
        token = test_session.refresh_token
        assert test_session.verify_refresh_token(token) is True
    
    def test_verify_refresh_token_invalid(self, test_session):
        assert test_session.verify_refresh_token("invalid_token") is False
    
    def test_set_access_token(self, test_session, db_session):
        test_session.set_access_token("access_token_123")
        db_session.commit()
        assert test_session.access_token == "access_token_123"


class TestSessionActions:
    """اختبارات إجراءات الجلسة"""
    
    def test_update_activity(self, test_session, db_session):
        old_activity = test_session.last_activity_at
        test_session.update_activity()
        db_session.commit()
        assert test_session.last_activity_at >= old_activity
    
    def test_refresh_expiry(self, test_session, db_session):
        old_expiry = test_session.expires_at
        test_session.refresh_expiry(days=10)
        db_session.commit()
        assert test_session.expires_at.replace(tzinfo=None) >= old_expiry.replace(tzinfo=None)
    
    def test_revoke(self, test_session, db_session):
        test_session.revoke('user_logout')
        db_session.commit()
        
        assert test_session.is_active is False
        assert test_session.status == SessionStatus.REVOKED
        assert test_session.revoked_at is not None
        assert test_session.revoke_reason == 'user_logout'
    
    def test_logout(self, test_session, db_session):
        test_session.logout()
        db_session.commit()
        assert test_session.status == SessionStatus.LOGGED_OUT
        assert test_session.is_active is False
    
    def test_expire(self, test_session, db_session):
        test_session.expire()
        db_session.commit()
        assert test_session.status == SessionStatus.EXPIRED
        assert test_session.is_active is False


class TestSessionManager:
    """اختبارات مدير الجلسات"""
    
    def test_find_by_refresh_token(self, db_session, test_session):
        found = SessionManager.find_by_refresh_token(
            db_session, test_session.refresh_token
        )
        assert found is not None
        assert found.id == test_session.id
    
    def test_find_active_by_user(self, db_session, test_user, test_session):
        active = SessionManager.find_active_by_user(db_session, str(test_user.id))
        assert len(active) >= 1
    
    def test_get_active_count(self, db_session, test_user, test_session):
        count = SessionManager.get_active_count(db_session, str(test_user.id))
        assert count >= 1
    
    def test_revoke_all_user_sessions(self, db_session, test_user):
        # إنشاء جلستين
        SessionManager.create_session(db_session, str(test_user.id))
        SessionManager.create_session(db_session, str(test_user.id))
        db_session.commit()
        
        count = SessionManager.revoke_all_user_sessions(
            db_session, str(test_user.id), reason='test_revoke'
        )
        assert count == 2
        
        active = SessionManager.find_active_by_user(db_session, str(test_user.id))
        assert len(active) == 0
    
    def test_revoke_all_except_current(self, db_session, test_user, test_session):
        # إنشاء جلسة إضافية
        sess2 = SessionManager.create_session(db_session, str(test_user.id))
        db_session.commit()
        
        count = SessionManager.revoke_all_user_sessions(
            db_session, str(test_user.id),
            exclude_session_id=str(test_session.id)
        )
        assert count == 1
        
        # الجلسة الحالية ما زالت نشطة
        db_session.refresh(test_session)
        assert test_session.is_active is True
    
    def test_cleanup_expired_sessions(self, db_session, test_user):
        # إنشاء جلسة منتهية
        sess = SessionManager.create_session(db_session, str(test_user.id))
        sess.expires_at = utc_now() - timedelta(days=60)
        db_session.commit()
        
        deleted = SessionManager.cleanup_expired_sessions(db_session, days_old=30)
        assert deleted >= 1
    
    def test_count_by_device_type(self, db_session, test_user, test_session):
        counts = SessionManager.count_by_device_type(db_session, str(test_user.id))
        assert isinstance(counts, dict)
    
    def test_get_user_devices(self, db_session, test_user, test_session):
        devices = SessionManager.get_user_devices(db_session, str(test_user.id))
        assert len(devices) >= 1
        assert 'fingerprint' in devices[0]
        assert 'device_type' in devices[0]


class TestSessionNewDevice:
    """اختبارات كشف الجهاز الجديد"""
    
    def test_is_new_device_first_time(self, db_session, test_session):
        # أول مرة - يجب أن يكون جهاز جديد
        assert test_session.is_new_device(db_session) is True
    
    def test_is_new_device_same_device(self, db_session, test_user, test_session):
        # إنشاء جلسة أخرى بنفس البصمة
        sess2 = Session(
            user_id=str(test_user.id),
            ip_address=test_session.ip_address,
            user_agent=test_session.user_agent
        )
        sess2.generate_refresh_token()
        db_session.add(sess2)
        db_session.commit()
        
        assert sess2.is_new_device(db_session) is False


class TestSessionSerialization:
    """اختبارات تحويل الجلسة إلى قاموس"""
    
    def test_to_dict(self, test_session):
        data = test_session.to_dict()
        assert 'id' in data
        assert 'user_id' in data
        assert 'device_type' in data
        assert 'refresh_token' not in data  # ليس في الوضع العادي
    
    def test_to_dict_include_sensitive(self, test_session):
        data = test_session.to_dict(include_sensitive=True)
        assert 'refresh_token' in data
        assert 'device_fingerprint' in data


class TestDeviceFingerprint:
    """اختبارات بصمة الجهاز"""
    
    def test_generate_fingerprint(self):
        fp1 = generate_device_fingerprint("Chrome", "192.168.1.1")
        fp2 = generate_device_fingerprint("Chrome", "192.168.1.1")
        assert fp1 == fp2
        assert len(fp1) == 32
    
    def test_fingerprint_different(self):
        fp1 = generate_device_fingerprint("Chrome", "192.168.1.1")
        fp2 = generate_device_fingerprint("Firefox", "192.168.1.1")
        assert fp1 != fp2


__all__ = [
    "TestUserAgentParsing",
    "TestSessionBasic",
    "TestSessionProperties",
    "TestSessionTokens",
    "TestSessionActions",
    "TestSessionManager",
    "TestSessionNewDevice",
    "TestSessionSerialization",
    "TestDeviceFingerprint",
]

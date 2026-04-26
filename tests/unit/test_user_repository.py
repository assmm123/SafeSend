"""
اختبارات مستودع المستخدم
Unit Tests for User Repository
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User, UserRole
from src.app.models.user_repository import UserRepository, PaginatedResult


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
def repo(db_session):
    """إنشاء مستودع المستخدم"""
    return UserRepository(db_session)


@pytest.fixture
def test_user(repo):
    """إنشاء مستخدم اختباري"""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User"
    )
    user.set_password("SecurePass123!")
    return repo.create(user)


class TestUserRepositoryBasic:
    """اختبارات أساسية للمستودع"""
    
    def test_create_user(self, repo):
        user = User(email="new@example.com", username="newuser")
        user.set_password("Pass123!")
        created = repo.create(user)
        
        assert created.id is not None
        assert created.email == "new@example.com"
    
    def test_get_by_id(self, repo, test_user):
        found = repo.get_by_id(test_user.id)
        assert found is not None
        assert found.id == test_user.id
        assert found.email == "test@example.com"
    
    def test_get_by_id_not_found(self, repo):
        found = repo.get_by_id(uuid4())
        assert found is None
    
    def test_get_by_email(self, repo, test_user):
        found = repo.get_by_email("test@example.com")
        assert found is not None
        assert found.email == "test@example.com"
    
    def test_get_by_email_case_insensitive(self, repo, test_user):
        found = repo.get_by_email("TEST@EXAMPLE.COM")
        assert found is not None
    
    def test_get_by_username(self, repo, test_user):
        found = repo.get_by_username("testuser")
        assert found is not None
        assert found.username == "testuser"
    
    def test_exists_by_email(self, repo, test_user):
        assert repo.exists_by_email("test@example.com") is True
        assert repo.exists_by_email("nonexistent@example.com") is False
    
    def test_exists_by_username(self, repo, test_user):
        assert repo.exists_by_username("testuser") is True
        assert repo.exists_by_username("nonexistent") is False


class TestUserRepositoryList:
    """اختبارات القوائم والتصفح"""
    
    def test_list_all(self, repo, test_user):
        users = repo.list_all()
        assert len(users) >= 1
    
    def test_list_all_with_filters(self, repo, test_user):
        users = repo.list_all(is_active=True)
        assert len(users) >= 1
        
        users = repo.list_all(is_active=False)
        assert len(users) == 0
    
    def test_list_all_excludes_deleted(self, repo, test_user):
        repo.delete(test_user.id)
        users = repo.list_all()
        assert len(users) == 0
        
        users = repo.list_all(include_deleted=True)
        assert len(users) == 1
    
    def test_paginate(self, repo):
        for i in range(5):
            user = User(email=f"user{i}@ex.com", username=f"user{i}")
            user.set_password("pass")
            repo.create(user)
        
        result = repo.paginate(page=1, page_size=2)
        assert result.total == repo.count()  # 5 + test_user
        assert len(result.items) == 2
        assert result.page == 1
        assert result.pages == 3
        assert result.has_next is True
        assert result.has_prev is False
    
    def test_paginate_to_dict(self, repo):
        result = repo.paginate(page=1, page_size=10)
        d = result.to_dict()
        assert "items" in d
        assert "total" in d
        assert "page" in d
    
    def test_search(self, repo, test_user):
        results = repo.search("test")
        assert len(results) >= 1
    
    def test_get_by_role(self, repo, test_user):
        users = repo.get_by_role(UserRole.USER)
        assert len(users) >= 1


class TestUserRepositoryStats:
    """اختبارات الإحصائيات"""
    
    def test_count(self, repo, test_user):
        assert repo.count() == 1
        assert repo.count(is_active=True) == 1
        assert repo.count(is_active=False) == 0
    
    def test_get_stats(self, repo, test_user):
        stats = repo.get_stats()
        assert stats["total"] == 1
        assert stats["active"] == 1
        assert "by_role" in stats
        assert "new_today" in stats


class TestUserRepositoryWrite:
    """اختبارات الكتابة"""
    
    def test_update(self, repo, test_user):
        test_user.full_name = "Updated Name"
        updated = repo.update(test_user)
        assert updated.full_name == "Updated Name"
    
    def test_delete_soft(self, repo, test_user):
        result = repo.delete(test_user.id, soft=True)
        assert result is True
        
        found = repo.get_by_id(test_user.id)
        assert found is None
        
        found_deleted = repo.get_by_id_include_deleted(test_user.id)
        assert found_deleted is not None
        assert found_deleted.is_deleted is True
    
    def test_delete_hard(self, repo, test_user):
        result = repo.delete(test_user.id, soft=False)
        assert result is True
        
        found = repo.get_by_id_include_deleted(test_user.id)
        assert found is None
    
    def test_restore(self, repo, test_user):
        repo.delete(test_user.id, soft=True)
        result = repo.restore(test_user.id)
        assert result is True
        
        found = repo.get_by_id(test_user.id)
        assert found is not None
        assert found.is_deleted is False
    
    def test_change_password(self, repo, test_user):
        old_hash = test_user.password_hash
        result = repo.change_password(test_user.id, "NewPass123!")
        assert result is True
        assert test_user.password_hash != old_hash
        assert test_user.check_password("NewPass123!") is True
    
    def test_record_login(self, repo, test_user):
        result = repo.record_login(test_user.id, "192.168.1.1")
        assert result is True
        assert test_user.last_login is not None
        assert test_user.login_count == 1
    
    def test_record_failed_attempt(self, repo, test_user):
        result = repo.record_failed_attempt(test_user.id)
        assert result is True
        assert test_user.failed_attempts == 1


class TestUserRepositoryBulk:
    """اختبارات العمليات المجمعة"""
    
    def test_bulk_create(self, repo):
        users = [
            User(email=f"bulk{i}@ex.com", username=f"bulk{i}")
            for i in range(3)
        ]
        for u in users:
            u.set_password("pass")
        
        created = repo.bulk_create(users)
        assert len(created) == 3
        assert all(u.id is not None for u in created)
    
    def test_bulk_update_status(self, repo):
        users = []
        for i in range(3):
            u = User(email=f"status{i}@ex.com", username=f"status{i}")
            u.set_password("pass")
            users.append(repo.create(u))
        
        ids = [u.id for u in users]
        count = repo.bulk_update_status(ids, False)
        repo.session.expire_all()
        assert count == 3
        
        for uid in ids:
            u = repo.get_by_id_include_deleted(uid)
            assert u.is_active is False
    
    def test_bulk_delete(self, repo):
        users = []
        for i in range(3):
            u = User(email=f"del{i}@ex.com", username=f"del{i}")
            u.set_password("pass")
            users.append(repo.create(u))
        
        ids = [u.id for u in users]
        count = repo.bulk_delete(ids, soft=True)
        assert count == 3
        
        assert repo.count() == 0


class TestUserRepositoryTokens:
    """اختبارات التوكنات"""
    
    def test_generate_verification_token(self, repo, test_user):
        token = repo.generate_verification_token(test_user.id)
        assert token is not None
        assert len(token) == 32
        assert test_user.email_verification_token == token
    
    def test_verify_email(self, repo, test_user):
        token = repo.generate_verification_token(test_user.id)
        result = repo.verify_email(test_user.id, token)
        assert result is True
        assert test_user.email_verified is True
    
    def test_generate_password_reset_token(self, repo, test_user):
        token = repo.generate_password_reset_token("test@example.com")
        assert token is not None
        assert test_user.password_reset_token == token
    
    def test_get_by_verification_token(self, repo, test_user):
        token = repo.generate_verification_token(test_user.id)
        found = repo.get_by_email_verification_token(token)
        assert found is not None
        assert found.id == test_user.id
    
    def test_get_by_password_reset_token(self, repo, test_user):
        token = repo.generate_password_reset_token("test@example.com")
        found = repo.get_by_password_reset_token(token)
        assert found is not None
        assert found.id == test_user.id


__all__ = [
    "TestUserRepositoryBasic",
    "TestUserRepositoryList",
    "TestUserRepositoryStats",
    "TestUserRepositoryWrite",
    "TestUserRepositoryBulk",
    "TestUserRepositoryTokens",
]

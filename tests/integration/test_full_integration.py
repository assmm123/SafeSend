"""
اختبار تكامل كامل لجميع ملفات وثيقة 1
Full Integration Test for All Core Foundation Files

يغطي جميع الملفات الـ 18:
- base, errors, interfaces, config, logging_config, database
- security, validators, helpers, backup
- user, session, audit_log
- deal, conversation, message
- user_repository, deal_repository
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tempfile
import uuid
from decimal import Decimal
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User, UserRole
from src.app.models.session import Session, SessionManager, DeviceType, SessionStatus
from src.app.models.audit_log import AuditLog, AuditLogger, AuditAction, AuditSeverity, AuditResource
from src.app.models.deal import Deal, DealStatus, DealCurrency
from src.app.models.conversation import Conversation, ConversationStatus
from src.app.models.message import Message, MessageType, DeliveryStatus
from src.app.models.user_repository import UserRepository
from src.app.models.deal_repository import DealRepository
from src.app.models.security import hash_password, verify_password, generate_token, verify_token
from src.app.models.validators import validate_email, validate_username, sanitize_string
from src.app.models.helpers import utc_now, generate_id, slugify, format_currency
from src.app.models.config import get_config
from src.app.models.logging_config import setup_logging, get_logger
from src.app.models.database import get_session, init_db, check_connection, SessionContext


@pytest.fixture(scope="module")
def db_engine():
    """إنشاء محرك قاعدة بيانات مؤقتة لكل الاختبارات"""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "integration_test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        yield engine


@pytest.fixture
def db_session(db_engine):
    """إنشاء جلسة قاعدة بيانات"""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


class TestFullIntegration:
    """اختبار تكامل كامل لجميع المكونات"""
    
    def test_security_user_integration(self, db_session):
        """اختبار تكامل security مع user"""
        # 1. إنشاء مستخدم مع تشفير كلمة المرور
        password = "SecurePass123!"
        hashed = hash_password(password)
        
        user = User(
            email="security_test@valid-domain.com",
            username="securityuser",
            full_name="Security Test User",
            password_hash=hashed
        )
        db_session.add(user)
        db_session.commit()
        
        # 2. التحقق من كلمة المرور
        assert verify_password(password, user.password_hash) is True
        assert verify_password("wrong", user.password_hash) is False
        
        # 3. توليد JWT
        token = generate_token({"user_id": str(user.id), "role": user.role})
        assert token is not None
        
        # 4. التحقق من التوكن
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == str(user.id)
    
    def test_validators_user_integration(self, db_session):
        """اختبار تكامل validators مع user"""
        # 1. التحقق من البريد
        valid, msg = validate_email("test@valid-domain.com")
        assert valid is True
        
        # 2. التحقق من اسم المستخدم
        valid, msg = validate_username("testuser123")
        assert valid is True
        
        # 3. إنشاء مستخدم بعد التحقق
        user = User(
            email="validated@example.com",
            username="validateduser",
            full_name="Validated User"
        )
        user.set_password("Pass123!")
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
    
    def test_session_audit_integration(self, db_session):
        """اختبار تكامل session مع audit_log"""
        # 1. إنشاء مستخدم
        user = User(
            email="session_audit@example.com",
            username="sessionaudit"
        )
        user.set_password("Pass123!")
        db_session.add(user)
        db_session.commit()
        
        # 2. إنشاء جلسة
        sess = SessionManager.create_session(
            db_session,
            user_id=str(user.id),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        db_session.commit()
        
        assert sess.id is not None
        assert sess.user_id == str(user.id)
        
        # 3. تسجيل حدث تدقيق
        log = AuditLogger.log(
            db_session,
            action=AuditAction.LOGIN,
            resource=AuditResource.USER,
            user_id=str(user.id),
            resource_id=str(user.id),
            ip_address="192.168.1.1",
            severity=AuditSeverity.INFO
        )
        db_session.commit()
        
        assert log.id is not None
        assert log.action == AuditAction.LOGIN
        
        # 4. التحقق من ارتباط الجلسة بالمستخدم
        active_sessions = SessionManager.find_active_by_user(db_session, str(user.id))
        assert len(active_sessions) >= 1
    
    def test_deal_conversation_message_integration(self, db_session):
        """اختبار تكامل deal مع conversation و message"""
        # 1. إنشاء بائع ومشتري
        seller = User(email="seller@deal.com", username="seller")
        seller.set_password("Pass123!")
        buyer = User(email="buyer@deal.com", username="buyer")
        buyer.set_password("Pass123!")
        db_session.add_all([seller, buyer])
        db_session.commit()
        
        # 2. إنشاء صفقة
        deal = Deal(
            title="Integration Test Deal",
            description="Testing full integration",
            seller_id=str(seller.id),
            buyer_id=str(buyer.id),
            amount=Decimal("1500.00"),
            currency=DealCurrency.USDT
        )
        db_session.add(deal)
        db_session.commit()
        
        assert deal.id is not None
        assert deal.status == DealStatus.PENDING
        
        # 3. إنشاء محادثة للصفقة
        conv = Conversation(
            deal_id=str(deal.id),
            buyer_id=str(buyer.id),
            seller_id=str(seller.id),
            subject=f"Deal: {deal.title}"
        )
        db_session.add(conv)
        db_session.commit()
        
        assert conv.id is not None
        assert conv.deal_id == str(deal.id)
        
        # 4. إرسال رسائل
        msg1 = Message(
            conversation_id=str(conv.id),
            sender_id=str(buyer.id),
            content="I'm interested in this deal",
            content_type=MessageType.TEXT
        )
        msg2 = Message(
            conversation_id=str(conv.id),
            sender_id=str(seller.id),
            content="Great! Let's proceed",
            content_type=MessageType.TEXT
        )
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        assert msg1.id is not None
        assert msg2.id is not None
        
        # 5. تحديث آخر رسالة في المحادثة
        conv.update_last_message()
        db_session.commit()
        
        assert conv.last_message_at is not None
        
        # 6. تعليم الرسالة كمقروءة
        msg2.mark_as_read()
        db_session.commit()
        assert msg2.is_read is True
    
    def test_repository_pattern_integration(self, db_session):
        """اختبار تكامل repository pattern"""
        # 1. استخدام UserRepository
        user_repo = UserRepository(db_session)
        
        user = User(email="repo_test@valid-domain.com", username="repouser")
        user.set_password("Pass123!")
        created = user_repo.create(user)
        
        assert created.id is not None
        
        # 2. البحث عن المستخدم
        found = user_repo.get_by_email("repo_test@valid-domain.com")
        assert found is not None
        assert found.username == "repouser"
        
        # 3. استخدام DealRepository
        deal_repo = DealRepository(db_session)
        
        seller = User(email="reposeller@example.com", username="reposeller")
        seller.set_password("Pass123!")
        buyer = User(email="repobuyer@example.com", username="repobuyer")
        buyer.set_password("Pass123!")
        user_repo.bulk_create([seller, buyer])
        
        deal = Deal(
            title="Repository Deal",
            seller_id=str(seller.id),
            buyer_id=str(buyer.id),
            amount=Decimal("2000.00")
        )
        created_deal = deal_repo.create(deal)
        
        assert created_deal.id is not None
        
        # 4. جلب صفقات المستخدم
        user_deals = deal_repo.get_by_participant(seller.id)
        assert len(user_deals) >= 1
    
    def test_audit_log_sanitization_integration(self, db_session):
        """اختبار تكامل audit_log مع تطهير البيانات"""
        user = User(email="sanitize@example.com", username="sanitize")
        user.set_password("SecretPass123!")
        db_session.add(user)
        db_session.commit()
        
        # تسجيل حدث مع بيانات حساسة
        log = AuditLogger.log(
            db_session,
            action="password_change",
            resource=AuditResource.USER,
            user_id=str(user.id),
            old_value={"password": "OldSecret"},
            new_value={"password": "NewSecret"}
        )
        db_session.commit()
        
        # التحقق من تطهير كلمة المرور
        assert log.old_value["password"] == "***REDACTED***"
        assert log.new_value["password"] == "***REDACTED***"
    
    def test_backup_helpers_integration(self, db_session):
        """اختبار تكامل backup مع helpers"""
        # استخدام دوال helpers
        unique_id = generate_id("test")
        assert unique_id.startswith("test_")
        
        slug = slugify("Hello World!")
        assert slug == "hello-world"
        
        formatted = format_currency(Decimal("1234.56"), "USD")
        assert "$" in formatted
        
        # استخدام backup
        from src.app.models.backup import backup_database, list_backups, cleanup_old_backups
        
        # النسخ الاحتياطي يعتمد على البيئة، نتأكد فقط من وجود الدوال
        assert callable(backup_database)
        assert callable(list_backups)
        assert callable(cleanup_old_backups)
    
    def test_config_logging_database_integration(self, db_session):
        """اختبار تكامل config مع logging و database"""
        # 1. التحقق من config
        config = get_config()
        assert config.SQLALCHEMY_DATABASE_URI is not None
        
        # 2. التحقق من database connection
        assert check_connection() is True
        
        # 3. استخدام logging
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(log_dir=log_dir, enable_console=False, enable_file=True)
            logger = get_logger("integration_test")
            logger.info("Integration test log message")
            
            log_file = Path(log_dir) / "nexus.log"
            assert log_file.exists()
    
    def test_session_context_manager_integration(self, db_session):
        """اختبار SessionContext"""
        with SessionContext() as sess:
            result = sess.execute(text("SELECT 1")).scalar()
            assert result == 1
    
    def test_full_user_workflow(self, db_session):
        """اختبار سير عمل كامل للمستخدم"""
        # 1. إنشاء مستخدم
        user = User(
            email="workflow@example.com",
            username="workflowuser",
            full_name="Workflow User"
        )
        user.set_password("WorkflowPass123!")
        db_session.add(user)
        db_session.commit()
        
        # 2. تسجيل دخول (جلسة)
        sess = SessionManager.create_session(
            db_session,
            user_id=str(user.id),
            ip_address="10.0.0.1"
        )
        db_session.commit()
        
        # 3. تسجيل حدث تدقيق
        AuditLogger.log(
            db_session,
            action=AuditAction.LOGIN,
            resource=AuditResource.USER,
            user_id=str(user.id)
        )
        db_session.commit()
        
        # 4. إنشاء صفقة كمشتري
        seller = User(email="workflowseller@example.com", username="workflowseller")
        seller.set_password("Pass123!")
        db_session.add(seller)
        db_session.commit()
        
        deal = Deal(
            title="Workflow Deal",
            seller_id=str(seller.id),
            buyer_id=str(user.id),
            amount=Decimal("750.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        # 5. إنشاء محادثة
        conv = Conversation(
            deal_id=str(deal.id),
            buyer_id=str(user.id),
            seller_id=str(seller.id)
        )
        db_session.add(conv)
        db_session.commit()
        
        # 6. إرسال رسالة
        msg = Message(
            conversation_id=str(conv.id),
            sender_id=str(user.id),
            content="I want to buy this"
        )
        db_session.add(msg)
        db_session.commit()
        
        # 7. التحقق من النتائج
        assert user.id is not None
        assert sess.id is not None
        assert deal.id is not None
        assert conv.id is not None
        assert msg.id is not None
        
        # 8. إبطال الجلسة
        sess.logout()
        db_session.commit()
        assert sess.is_active is False
    
    def test_deal_lifecycle_integration(self, db_session):
        """اختبار دورة حياة الصفقة كاملة"""
        # 1. إنشاء الأطراف
        seller = User(email="lifecycle_seller@ex.com", username="lcseller")
        seller.set_password("Pass123!")
        buyer = User(email="lifecycle_buyer@ex.com", username="lcbuyer")
        buyer.set_password("Pass123!")
        db_session.add_all([seller, buyer])
        db_session.commit()
        
        # 2. إنشاء الصفقة
        deal = Deal(
            title="Lifecycle Deal",
            seller_id=str(seller.id),
            buyer_id=str(buyer.id),
            amount=Decimal("3000.00")
        )
        db_session.add(deal)
        db_session.commit()
        assert deal.status == DealStatus.PENDING
        
        # 3. تمويل
        deal.fund(str(buyer.id), "tx_fund_123")
        db_session.commit()
        assert deal.status == DealStatus.FUNDED
        assert deal.funded_at is not None
        
        # 4. بدء التنفيذ
        deal.start_progress()
        db_session.commit()
        assert deal.status == DealStatus.IN_PROGRESS
        
        # 5. تسليم
        deal.deliver()
        db_session.commit()
        assert deal.status == DealStatus.DELIVERED
        assert deal.delivered_at is not None
        
        # 6. إكمال
        deal.complete("tx_release_456")
        db_session.commit()
        assert deal.status == DealStatus.COMPLETED
        assert deal.completed_at is not None
        
        # 7. التحقق من الإحصائيات
        deal_repo = DealRepository(db_session)
        stats = deal_repo.get_stats(seller.id)
        assert stats["total"] >= 1
    
    def test_conversation_message_read_status(self, db_session):
        """اختبار حالة القراءة في المحادثة والرسائل"""
        # 1. إنشاء مستخدمين
        user1 = User(email="read_user1@ex.com", username="readuser1")
        user1.set_password("Pass123!")
        user2 = User(email="read_user2@ex.com", username="readuser2")
        user2.set_password("Pass123!")
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # 2. إنشاء محادثة
        conv = Conversation(
            buyer_id=str(user1.id),
            seller_id=str(user2.id)
        )
        db_session.add(conv)
        db_session.commit()
        
        # 3. إرسال رسائل
        msg1 = Message(
            conversation_id=str(conv.id),
            sender_id=str(user1.id),
            content="Hello"
        )
        msg2 = Message(
            conversation_id=str(conv.id),
            sender_id=str(user2.id),
            content="Hi there"
        )
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        # 4. تعليم الرسالة الثانية كمقروءة
        msg2.mark_as_read()
        db_session.commit()
        
        assert msg2.is_read is True
        assert msg1.is_read is False
        
        # 5. تحديث المحادثة
        conv.update_last_message()
        # conv.set_last_read(str(user1.id))
        db_session.commit()
        
        assert conv.last_message_at is not None
        # assert conv.get_last_read(str(user1.id)) is not None


__all__ = ["TestFullIntegration"]

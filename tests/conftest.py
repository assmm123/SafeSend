"""
تكوين pytest للاختبارات
Pytest Configuration

يوفر fixtures مشتركة لجميع الاختبارات
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# إضافة المسار الجذر
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app.models.base import Base


@pytest.fixture(scope="function")
def db_engine():
    """إنشاء محرك قاعدة بيانات مؤقتة"""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(engine)
        yield engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """إنشاء جلسة قاعدة بيانات"""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def clean_db(db_engine):
    """تنظيف قاعدة البيانات قبل كل اختبار"""
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    yield
    Base.metadata.drop_all(db_engine)


@pytest.fixture
def temp_dir():
    """إنشاء مجلد مؤقت"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def pytest_configure(config):
    """تكوين pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """تعديل العناصر المجمعة"""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

# ============================================
# Deal Fixtures
# ============================================

@pytest.fixture
def deal(db_session, seller, buyer):
    """إنشاء صفقة للاختبار"""
    from src.app.models.deal import Deal, DealCurrency
    from decimal import Decimal
    
    deal = Deal(
        title="Test Deal",
        description="Test description",
        seller_id=seller.id,
        buyer_id=buyer.id,
        amount=Decimal("100.00"),
        currency=DealCurrency.USDT
    )
    db_session.add(deal)
    db_session.commit()
    return deal


@pytest.fixture
def funded_deal(db_session, deal, buyer):
    """إنشاء صفقة ممولة"""
    deal.fund(buyer.id, "test_tx_123")
    db_session.commit()
    return deal


@pytest.fixture
def completed_deal(db_session, funded_deal):
    """إنشاء صفقة مكتملة"""
    funded_deal.start_progress()
    funded_deal.deliver()
    funded_deal.complete("release_tx_456")
    db_session.commit()
    return funded_deal


@pytest.fixture
def disputed_deal(db_session, funded_deal):
    """إنشاء صفقة متنازع عليها"""
    funded_deal.dispute("Test dispute reason")
    db_session.commit()
    return funded_deal


@pytest.fixture
def other_user(db_session):
    """إنشاء مستخدم آخر للاختبار"""
    from src.app.models.user import User, UserRole
    import uuid
    
    user = User(
        email=f"other_{uuid.uuid4().hex[:8]}@test.com",
        username=f"other_{uuid.uuid4().hex[:8]}",
        full_name="Other User",
        role=UserRole.USER
    )
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    return user

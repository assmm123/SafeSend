"""
اختبارات مستودع الصفقات
Unit Tests for Deal Repository
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tempfile
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.deal import Deal, DealStatus, DealCurrency
from src.app.models.deal_repository import DealRepository, PaginatedDealResult


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
    """إنشاء مستودع الصفقات"""
    return DealRepository(db_session)


@pytest.fixture
def seller(db_session):
    """إنشاء بائع"""
    u = User(email="seller@test.com", username="seller")
    u.set_password("pass")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def buyer(db_session):
    """إنشاء مشتري"""
    u = User(email="buyer@test.com", username="buyer")
    u.set_password("pass")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def test_deal(repo, seller, buyer):
    """إنشاء صفقة اختبارية"""
    deal = Deal(
        title="Test Deal",
        description="Test Description",
        seller_id=str(seller.id),
        buyer_id=str(buyer.id),
        amount=Decimal("1000.00"),
        currency=DealCurrency.USDT
    )
    return repo.create(deal)


class TestDealRepositoryBasic:
    """اختبارات أساسية للمستودع"""
    
    def test_create_deal(self, repo, seller, buyer):
        deal = Deal(
            title="New Deal",
            seller_id=str(seller.id),
            buyer_id=str(buyer.id),
            amount=Decimal("500.00")
        )
        created = repo.create(deal)
        
        assert created.id is not None
        assert created.title == "New Deal"
        assert created.status == DealStatus.PENDING
    
    def test_get_by_id(self, repo, test_deal):
        found = repo.get_by_id(test_deal.id)
        assert found is not None
        assert found.id == test_deal.id
        assert found.title == "Test Deal"
    
    def test_get_by_id_not_found(self, repo):
        found = repo.get_by_id(uuid4())
        assert found is None
    
    def test_get_by_buyer(self, repo, test_deal, buyer):
        deals = repo.get_by_buyer(buyer.id)
        assert len(deals) >= 1
        assert deals[0].buyer_id == str(buyer.id)
    
    def test_get_by_seller(self, repo, test_deal, seller):
        deals = repo.get_by_seller(seller.id)
        assert len(deals) >= 1
        assert deals[0].seller_id == str(seller.id)
    
    def test_get_by_participant(self, repo, test_deal, seller, buyer):
        deals_seller = repo.get_by_participant(seller.id)
        deals_buyer = repo.get_by_participant(buyer.id)
        assert len(deals_seller) >= 1
        assert len(deals_buyer) >= 1
    
    def test_get_active_for_user(self, repo, test_deal, seller):
        active = repo.get_active_for_user(seller.id)
        assert len(active) >= 1


class TestDealRepositoryList:
    """اختبارات القوائم والتصفح"""
    
    def test_list_all(self, repo, test_deal):
        deals = repo.list_all()
        assert len(deals) >= 1
    
    def test_list_all_with_filters(self, repo, test_deal, seller):
        deals = repo.list_all(seller_id=seller.id)
        assert len(deals) >= 1
        
        deals = repo.list_all(status=DealStatus.PENDING)
        assert len(deals) >= 1
        
        deals = repo.list_all(status=DealStatus.COMPLETED)
        assert len(deals) == 0
    
    def test_list_by_status(self, repo, test_deal):
        deals = repo.list_by_status(DealStatus.PENDING)
        assert len(deals) >= 1
    
    def test_paginate(self, repo, seller, buyer):
        for i in range(5):
            deal = Deal(
                title=f"Deal {i}",
                seller_id=str(seller.id),
                buyer_id=str(buyer.id),
                amount=Decimal("100.00")
            )
            repo.create(deal)
        
        result = repo.paginate(page=1, page_size=2)
        assert result.total >= 5
        assert len(result.items) == 2
        assert result.page == 1
        assert result.has_next is True
    
    def test_paginate_to_dict(self, repo):
        result = repo.paginate(page=1, page_size=10)
        d = result.to_dict()
        assert "items" in d
        assert "total" in d
        assert "page" in d
    
    def test_search(self, repo, test_deal):
        results = repo.search("Test")
        assert len(results) >= 1


class TestDealRepositoryExpiredDisputed:
    """اختبارات الصفقات المنتهية والمتنازع عليها"""
    
    def test_get_expired_deals(self, repo):
        deals = repo.get_expired_deals()
        assert isinstance(deals, list)
    
    def test_get_disputed_deals(self, repo):
        deals = repo.get_disputed_deals()
        assert isinstance(deals, list)
    
    def test_check_and_expire_deals(self, repo, test_deal):
        from src.app.models.helpers import utc_now
        from datetime import timedelta
        
        test_deal.deadline = utc_now() - timedelta(days=1)
        repo.update(test_deal)
        
        count = repo.check_and_expire_deals()
        assert count >= 1
        
        repo.session.refresh(test_deal)
        assert test_deal.status == DealStatus.EXPIRED


class TestDealRepositoryWrite:
    """اختبارات الكتابة"""
    
    def test_update(self, repo, test_deal):
        test_deal.title = "Updated Title"
        updated = repo.update(test_deal)
        assert updated.title == "Updated Title"
    
    def test_update_status(self, repo, test_deal, buyer):
        # تمويل الصفقة أولاً
        test_deal.status = DealStatus.FUNDED
        repo.update(test_deal)
        
        updated = repo.update_status(test_deal.id, DealStatus.IN_PROGRESS)
        assert updated is not None
        assert updated.status == DealStatus.IN_PROGRESS
    
    def test_update_status_invalid_transition(self, repo, test_deal):
        # لا يمكن الانتقال من PENDING إلى COMPLETED مباشرة
        updated = repo.update_status(test_deal.id, DealStatus.COMPLETED)
        assert updated is None
    
    def test_delete(self, repo, seller, buyer):
        deal = Deal(
            title="To Delete",
            seller_id=str(seller.id),
            buyer_id=str(buyer.id),
            amount=Decimal("100.00")
        )
        created = repo.create(deal)
        
        result = repo.delete(created.id)
        assert result is True
        
        found = repo.get_by_id(created.id)
        assert found is None
    
    def test_delete_non_pending(self, repo, test_deal):
        test_deal.status = DealStatus.FUNDED
        repo.update(test_deal)
        
        result = repo.delete(test_deal.id)
        assert result is False


class TestDealRepositoryStats:
    """اختبارات الإحصائيات"""
    
    def test_count(self, repo, test_deal):
        assert repo.count() >= 1
        assert repo.count(status=DealStatus.PENDING) >= 1
        assert repo.count(status=DealStatus.COMPLETED) == 0
    
    def test_count_by_status(self, repo, test_deal):
        counts = repo.count_by_status()
        assert DealStatus.PENDING in counts
        assert counts[DealStatus.PENDING] >= 1
    
    def test_get_total_volume(self, repo, test_deal):
        test_deal.status = DealStatus.COMPLETED
        repo.update(test_deal)
        
        volume = repo.get_total_volume()
        assert volume == Decimal("1000.00")
    
    def test_get_stats(self, repo, test_deal):
        stats = repo.get_stats()
        assert "total" in stats
        assert "by_status" in stats
        assert "total_volume_usdt" in stats
        assert "completion_rate" in stats
        assert "active_count" in stats


class TestDealRepositoryIntegration:
    """اختبارات تكاملية"""
    
    def test_full_deal_flow(self, repo, seller, buyer):
        # 1. إنشاء صفقة
        deal = Deal(
            title="Flow Test",
            seller_id=str(seller.id),
            buyer_id=str(buyer.id),
            amount=Decimal("500.00")
        )
        created = repo.create(deal)
        assert created.status == DealStatus.PENDING
        
        # 2. تمويل
        updated = repo.update_status(created.id, DealStatus.FUNDED)
        assert updated.status == DealStatus.FUNDED
        
        # 3. بدء التنفيذ
        updated = repo.update_status(created.id, DealStatus.IN_PROGRESS)
        assert updated.status == DealStatus.IN_PROGRESS
        
        # 4. تسليم
        updated = repo.update_status(created.id, DealStatus.DELIVERED)
        assert updated.status == DealStatus.DELIVERED
        
        # 5. إكمال
        updated = repo.update_status(created.id, DealStatus.COMPLETED)
        assert updated.status == DealStatus.COMPLETED
        
        # 6. التحقق من الإحصائيات
        stats = repo.get_stats(seller.id)
        assert stats["total"] >= 1


__all__ = [
    "TestDealRepositoryBasic",
    "TestDealRepositoryList",
    "TestDealRepositoryExpiredDisputed",
    "TestDealRepositoryWrite",
    "TestDealRepositoryStats",
    "TestDealRepositoryIntegration",
]

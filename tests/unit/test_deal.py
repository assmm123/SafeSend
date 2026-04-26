"""
اختبارات نموذج الصفقة
Deal Model Tests
"""

import uuid
from decimal import Decimal
from datetime import timedelta

import pytest

from src.app.models.deal import Deal, DealStatus, DealCurrency, PLATFORM_FEE_PERCENT
from src.app.models.helpers import utc_now


class TestDealBasic:
    """اختبارات أساسية للصفقة"""
    
    def test_create_deal(self, db_session, seller):
        """اختبار إنشاء صفقة"""
        deal = Deal(
            title="Test Deal",
            description="Test description",
            seller_id=seller.id,
            amount=Decimal("100.00"),
            currency=DealCurrency.USDT
        )
        
        db_session.add(deal)
        db_session.commit()
        
        assert deal.id is not None
        assert deal.title == "Test Deal"
        assert deal.status == DealStatus.PENDING
        assert deal.amount == Decimal("100.00")
        assert deal.platform_fee == Decimal("1.00")  # 1%
        assert deal.seller_amount == Decimal("99.00")
        assert deal.deadline is not None
    
    def test_deal_relationships(self, db_session, seller, buyer):
        """اختبار علاقات الصفقة"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        
        db_session.add(deal)
        db_session.commit()
        
        assert deal.seller.id == seller.id
        assert deal.buyer.id == buyer.id
        assert deal.is_participant(seller.id) is True
        assert deal.is_participant(buyer.id) is True
        assert deal.get_other_party(seller.id) == buyer.id
        assert deal.get_other_party(buyer.id) == seller.id
    
    def test_deal_default_deadline(self, db_session, seller):
        """اختبار الموعد النهائي الافتراضي (7 أيام)"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            amount=Decimal("100.00")
        )
        
        db_session.add(deal)
        db_session.commit()
        
        expected_deadline = deal.created_at + timedelta(days=7)
        assert deal.deadline is not None
        # مقارنة مع هامش خطأ بسيط
        diff = abs((deal.deadline - expected_deadline).total_seconds())
        assert diff < 1


class TestDealTransitions:
    """اختبارات انتقالات الحالات"""
    
    def test_fund_deal(self, db_session, seller, buyer):
        """اختبار تمويل الصفقة"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        assert deal.status == DealStatus.PENDING
        assert deal.can_be_funded is True
        
        deal.fund(buyer.id, "tx_123")
        db_session.commit()
        
        assert deal.status == DealStatus.FUNDED
        assert deal.escrow_tx_id == "tx_123"
        assert deal.funded_at is not None
    
    def test_fund_deal_wrong_buyer(self, db_session, seller, buyer, other_user):
        """اختبار تمويل الصفقة من مشتري غير صحيح"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        with pytest.raises(ValueError, match="Only buyer can fund"):
            deal.fund(other_user.id, "tx_123")
    
    def test_start_progress(self, db_session, seller, buyer):
        """اختبار بدء العمل"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        deal.fund(buyer.id, "tx_123")
        db_session.commit()
        
        deal.start_progress()
        db_session.commit()
        
        assert deal.status == DealStatus.IN_PROGRESS
    
    def test_deliver_deal(self, db_session, seller, buyer):
        """اختبار تسليم العمل"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        deal.fund(buyer.id, "tx_123")
        deal.start_progress()
        db_session.commit()
        
        deal.deliver()
        db_session.commit()
        
        assert deal.status == DealStatus.DELIVERED
        assert deal.delivered_at is not None
    
    def test_complete_deal(self, db_session, seller, buyer):
        """اختبار إكمال الصفقة"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        deal.fund(buyer.id, "tx_123")
        deal.start_progress()
        deal.deliver()
        db_session.commit()
        
        deal.complete("release_tx_456")
        db_session.commit()
        
        assert deal.status == DealStatus.COMPLETED
        assert deal.completed_at is not None
        assert deal.release_tx_id == "release_tx_456"
    
    def test_cancel_deal(self, db_session, seller, buyer):
        """اختبار إلغاء الصفقة"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        assert deal.can_be_cancelled is True
        
        deal.cancel("Changed mind", "buyer")
        db_session.commit()
        
        assert deal.status == DealStatus.CANCELLED
        assert deal.cancelled_at is not None
        assert "Changed mind" in deal.cancel_reason
    
    def test_dispute_deal(self, db_session, seller, buyer):
        """اختبار فتح نزاع"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        deal.fund(buyer.id, "tx_123")
        db_session.commit()
        
        deal.dispute("Work not as described")
        db_session.commit()
        
        assert deal.status == DealStatus.DISPUTED
        assert deal.dispute_reason == "Work not as described"
    
    def test_resolve_dispute_refund(self, db_session, seller, buyer):
        """اختبار حل النزاع مع استرداد"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        deal.fund(buyer.id, "tx_123")
        deal.dispute("Issue")
        db_session.commit()
        
        deal.resolve_dispute("Resolved in favor of buyer", refund=True)
        db_session.commit()
        
        assert deal.status == DealStatus.REFUNDED
        assert deal.dispute_resolved_at is not None
    
    def test_resolve_dispute_complete(self, db_session, seller, buyer):
        """اختبار حل النزاع مع إكمال"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        deal.fund(buyer.id, "tx_123")
        deal.dispute("Issue")
        db_session.commit()
        
        deal.resolve_dispute("Resolved in favor of seller", refund=False)
        db_session.commit()
        
        assert deal.status == DealStatus.COMPLETED
        assert deal.dispute_resolved_at is not None
    
    def test_invalid_transition(self, db_session, seller, buyer):
        """اختبار انتقال غير صالح"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        # لا يمكن التسليم قبل التمويل
        with pytest.raises(ValueError):
            deal.deliver()
        
        # لا يمكن الإكمال قبل التسليم
        deal.fund(buyer.id, "tx_123")
        db_session.commit()
        
        with pytest.raises(ValueError):
            deal.complete()


class TestDealProperties:
    """اختبارات خصائص الصفقة"""
    
    def test_is_expired(self, db_session, seller):
        """اختبار انتهاء الصلاحية"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            amount=Decimal("100.00")
        )
        # تعيين موعد نهائي في الماضي
        deal.deadline = utc_now() - timedelta(days=1)
        db_session.add(deal)
        db_session.commit()
        
        assert deal.is_expired is True
    
    def test_is_active(self, db_session, seller, buyer):
        """اختبار الحالة النشطة"""
        deal = Deal(
            title="Test Deal",
            seller_id=seller.id,
            buyer_id=buyer.id,
            amount=Decimal("100.00")
        )
        db_session.add(deal)
        db_session.commit()
        
        assert deal.is_active is True  # PENDING
        
        deal.fund(buyer.id, "tx_123")
        db_session.commit()
        assert deal.is_active is True  # FUNDED
        
        deal.start_progress()
        db_session.commit()
        assert deal.is_active is True  # IN_PROGRESS
        
        deal.deliver()
        db_session.commit()
        assert deal.is_active is True  # DELIVERED
        
        deal.complete()
        db_session.commit()
        assert deal.is_active is False  # COMPLETED
    
    def test_platform_fee_calculation(self, db_session, seller):
        """اختبار حساب رسوم المنصة"""
        test_cases = [
            (Decimal("100.00"), Decimal("1.00"), Decimal("99.00")),
            (Decimal("50.00"), Decimal("0.50"), Decimal("49.50")),
            (Decimal("1000.00"), Decimal("10.00"), Decimal("990.00")),
        ]
        
        for amount, expected_fee, expected_seller in test_cases:
            deal = Deal(
                title="Test Deal",
                seller_id=seller.id,
                amount=amount
            )
            db_session.add(deal)
            
            assert deal.platform_fee == expected_fee
            assert deal.seller_amount == expected_seller


class TestDealFixtures:
    """اختبارات الـ fixtures"""
    
    def test_create_funded_deal(self, db_session, funded_deal):
        """اختبار fixture صفقة ممولة"""
        assert funded_deal.status == DealStatus.FUNDED
        assert funded_deal.escrow_tx_id is not None
        assert funded_deal.funded_at is not None
    
    def test_create_completed_deal(self, db_session, completed_deal):
        """اختبار fixture صفقة مكتملة"""
        assert completed_deal.status == DealStatus.COMPLETED
        assert completed_deal.completed_at is not None
    
    def test_create_disputed_deal(self, db_session, disputed_deal):
        """اختبار fixture صفقة متنازع عليها"""
        assert disputed_deal.status == DealStatus.DISPUTED
        assert disputed_deal.dispute_reason is not None


__all__ = [
    "TestDealBasic",
    "TestDealTransitions",
    "TestDealProperties",
    "TestDealFixtures",
]

"""
مستودع الصفقات
Deal Repository

نمط Repository لعزل عمليات قاعدة البيانات الخاصة بالصفقات
ينفذ IDealRepository من interfaces.py
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.app.models.deal import Deal, DealStatus, DealCurrency
from src.app.models.interfaces import IDealRepository
from src.app.models.helpers import utc_now
from src.app.models.logging_config import get_logger

logger = get_logger(__name__)


# ============================================
# Pagination Result
# ============================================

@dataclass
class PaginatedDealResult:
    """نتيجة التصفح للصفقات"""
    items: List[Deal]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


# ============================================
# Deal Repository
# ============================================

class DealRepository(IDealRepository):
    """
    مستودع الصفقات
    Deal Repository
    
    يغلف جميع عمليات قاعدة البيانات المتعلقة بالصفقات
    """
    
    def __init__(self, session: Session):
        """
        تهيئة المستودع مع جلسة قاعدة البيانات
        
        Args:
            session (Session): جلسة SQLAlchemy
        """
        self.session = session
    
    # ============================================
    # عمليات القراءة الأساسية
    # ============================================
    
    def get_by_id(self, deal_id: UUID) -> Optional[Deal]:
        """جلب صفقة بواسطة المعرف"""
        return self.session.query(Deal).filter(Deal.id == deal_id).first()
    
    def get_by_buyer(self, buyer_id: UUID, include_completed: bool = True) -> List[Deal]:
        """جلب صفقات المشتري"""
        query = self.session.query(Deal).filter(Deal.buyer_id == str(buyer_id))
        if not include_completed:
            query = query.filter(Deal.status.in_([
                DealStatus.PENDING, DealStatus.FUNDED,
                DealStatus.IN_PROGRESS, DealStatus.DELIVERED,
                DealStatus.DISPUTED
            ]))
        return query.order_by(Deal.created_at.desc()).all()
    
    def get_by_seller(self, seller_id: UUID, include_completed: bool = True) -> List[Deal]:
        """جلب صفقات البائع"""
        query = self.session.query(Deal).filter(Deal.seller_id == str(seller_id))
        if not include_completed:
            query = query.filter(Deal.status.in_([
                DealStatus.PENDING, DealStatus.FUNDED,
                DealStatus.IN_PROGRESS, DealStatus.DELIVERED,
                DealStatus.DISPUTED
            ]))
        return query.order_by(Deal.created_at.desc()).all()
    
    def get_stalled(self, hours: int = 48) -> List[Deal]:
        """
        جلب الصفقات المتوقفة
        
        Args:
            hours: عدد ساعات التوقف
            
        Returns:
            list: الصفقات المتوقفة
        """
        from datetime import timedelta
        cutoff = utc_now() - timedelta(hours=hours)
        return self.session.query(Deal).filter(
            Deal.status.in_([DealStatus.FUNDED, DealStatus.IN_PROGRESS]),
            Deal.updated_at < cutoff,
            Deal.deleted_at.is_(None)
        ).all()


__all__ = ["DealRepository", "PaginatedDealResult"]

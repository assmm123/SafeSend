"""
نموذج الصفقة المتقدم
Advanced Deal Model

يمثل الصفقات بين البائع والمشتري مع:
- انتقالات محكومة للحالات
- حساب تلقائي للرسوم
- دعم النزاعات
- تتبع المعاملات المالية
- فهارس محسنة
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, DateTime, ForeignKey, Index,
    Numeric, String, Text, JSON
)
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


class DealStatus:
    """حالات الصفقة"""
    PENDING = "pending"
    FUNDED = "funded"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class DealCurrency:
    """العملات المدعومة"""
    USDT = "USDT"
    USD = "USD"
    TRX = "TRX"


PLATFORM_FEE_PERCENT = Decimal("1.0")

VALID_TRANSITIONS = {
    DealStatus.PENDING: [DealStatus.FUNDED, DealStatus.CANCELLED, DealStatus.EXPIRED],
    DealStatus.FUNDED: [DealStatus.IN_PROGRESS, DealStatus.DISPUTED, DealStatus.CANCELLED, DealStatus.EXPIRED],
    DealStatus.IN_PROGRESS: [DealStatus.DELIVERED, DealStatus.DISPUTED, DealStatus.EXPIRED],
    DealStatus.DELIVERED: [DealStatus.COMPLETED, DealStatus.DISPUTED],
    DealStatus.DISPUTED: [DealStatus.COMPLETED, DealStatus.REFUNDED],
    DealStatus.CANCELLED: [DealStatus.REFUNDED],
    DealStatus.COMPLETED: [],
    DealStatus.REFUNDED: [],
    DealStatus.EXPIRED: [],
}


class Deal(BaseModel):
    """
    نموذج الصفقة المتقدم
    Advanced Deal Model
    """
    
    __tablename__ = "deals"
    
    # ============================================
    # العلاقات - متوافقة مع base.py (UUID)
    # ============================================
    
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        index=False,
        doc="معرف البائع"
    )
    
    buyer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=False,
        doc="معرف المشتري"
    )
    
    seller = relationship('User', foreign_keys=[seller_id])
    buyer = relationship('User', foreign_keys=[buyer_id])
    
    # ============================================
    # معلومات أساسية
    # ============================================
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ============================================
    # المبالغ المالية
    # ============================================
    
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default=DealCurrency.USDT, nullable=False)
    platform_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    seller_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # ============================================
    # الحالة
    # ============================================
    
    status: Mapped[str] = mapped_column(String(20), default=DealStatus.PENDING, nullable=False)
    
    # ============================================
    # معاملات البلوكشين
    # ============================================
    
    escrow_address: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)
    escrow_tx_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    release_tx_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    refund_tx_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_memo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ============================================
    # التواريخ
    # ============================================
    
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    funded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # النزاعات
    # ============================================
    
    dispute_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    dispute_resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # ============================================
    # الحذف الناعم
    # ============================================
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # بيانات إضافية
    # ============================================
    
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # ============================================
    # الفهارس
    # ============================================
    
    __table_args__ = (
        Index('ix_deals_seller_id', 'seller_id'),
        Index('ix_deals_buyer_id', 'buyer_id'),
        Index('ix_deals_status', 'status'),
        Index('ix_deals_created_at', 'created_at'),
        Index('ix_deals_deadline', 'deadline'),
        Index('ix_deals_deleted_at', 'deleted_at'),
    )
    
    # ============================================
    # التهيئة
    # ============================================
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if self.amount is not None:
            if not isinstance(self.amount, Decimal):
                self.amount = Decimal(str(self.amount))
            if not self.platform_fee:
                self.platform_fee = self.amount * (PLATFORM_FEE_PERCENT / Decimal("100"))
                self.seller_amount = self.amount - self.platform_fee
        
        if self.deadline is None:
            self.deadline = utc_now() + timedelta(days=7)
        elif self.deadline.tzinfo is None:
            self.deadline = self.deadline.replace(tzinfo=timezone.utc)
    
    # ============================================
    # الخصائص
    # ============================================
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    @property
    def is_expired(self) -> bool:
        if self.deadline is None:
            return False
        if self.deadline.tzinfo is None:
            self.deadline = self.deadline.replace(tzinfo=timezone.utc)
        return utc_now() > self.deadline
    
    @property
    def is_active(self) -> bool:
        return not self.is_deleted and self.status in [
            DealStatus.PENDING, DealStatus.FUNDED,
            DealStatus.IN_PROGRESS, DealStatus.DELIVERED
        ]
    
    @property
    def can_be_cancelled(self) -> bool:
        return not self.is_deleted and self.status in [DealStatus.PENDING, DealStatus.FUNDED]
    
    @property
    def can_be_funded(self) -> bool:
        return not self.is_deleted and self.status == DealStatus.PENDING and self.buyer_id is not None
    
    # ============================================
    # دوال الحذف الناعم
    # ============================================
    
    def soft_delete(self) -> None:
        self.deleted_at = utc_now()
    
    def restore(self) -> None:
        self.deleted_at = None
    
    # ============================================
    # دوال الانتقال بين الحالات
    # ============================================
    
    def can_transition_to(self, new_status: str) -> bool:
        return new_status in VALID_TRANSITIONS.get(self.status, [])
    
    def _transition_to(self, new_status: str) -> bool:
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        self.status = new_status
        return True
    
    def fund(self, buyer_id: uuid.UUID, tx_id: str) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if not self.can_be_funded:
            raise ValueError("Deal cannot be funded")
        if self.buyer_id != buyer_id:
            raise ValueError("Only buyer can fund")
        self._transition_to(DealStatus.FUNDED)
        self.escrow_tx_id = tx_id
        self.funded_at = utc_now()
    
    def start_progress(self) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if self.status != DealStatus.FUNDED:
            raise ValueError("Deal must be funded")
        self._transition_to(DealStatus.IN_PROGRESS)
    
    def deliver(self) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if self.status != DealStatus.IN_PROGRESS:
            raise ValueError("Deal must be in progress")
        self._transition_to(DealStatus.DELIVERED)
        self.delivered_at = utc_now()
    
    def complete(self, release_tx_id: Optional[str] = None) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if self.status not in [DealStatus.DELIVERED, DealStatus.DISPUTED]:
            raise ValueError("Cannot complete")
        self._transition_to(DealStatus.COMPLETED)
        self.completed_at = utc_now()
        if release_tx_id:
            self.release_tx_id = release_tx_id
    
    def cancel(self, reason: str, cancelled_by: str) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if not self.can_be_cancelled:
            raise ValueError("Cannot cancel")
        self._transition_to(DealStatus.CANCELLED)
        self.cancelled_at = utc_now()
        self.cancel_reason = f"{reason} (by {cancelled_by})"
    
    def dispute(self, reason: str) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if self.status not in [DealStatus.FUNDED, DealStatus.IN_PROGRESS, DealStatus.DELIVERED]:
            raise ValueError("Cannot dispute")
        self._transition_to(DealStatus.DISPUTED)
        self.dispute_reason = reason
    
    def resolve_dispute(self, resolution: str, refund: bool = False, note: Optional[str] = None) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if self.status != DealStatus.DISPUTED:
            raise ValueError("Not disputed")
        if refund:
            self._transition_to(DealStatus.REFUNDED)
        else:
            self._transition_to(DealStatus.COMPLETED)
            self.completed_at = utc_now()
        self.dispute_resolved_at = utc_now()
        self.resolution_note = note or resolution
    
    def refund(self, tx_id: str) -> None:
        if self.is_deleted:
            raise ValueError("Deal is deleted")
        if self.status not in [DealStatus.CANCELLED, DealStatus.DISPUTED]:
            raise ValueError("Cannot refund")
        self._transition_to(DealStatus.REFUNDED)
        self.refund_tx_id = tx_id
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def get_other_party(self, user_id: uuid.UUID) -> Optional[uuid.UUID]:
        if user_id == self.seller_id:
            return self.buyer_id
        elif user_id == self.buyer_id:
            return self.seller_id
        return None
    
    def is_participant(self, user_id: uuid.UUID) -> bool:
        return user_id in [self.seller_id, self.buyer_id]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "status": self.status,
            "amount": float(self.amount) if self.amount else None,
            "currency": self.currency,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<Deal id={self.id} status={self.status}>"


__all__ = ["Deal", "DealStatus", "DealCurrency", "PLATFORM_FEE_PERCENT", "VALID_TRANSITIONS"]

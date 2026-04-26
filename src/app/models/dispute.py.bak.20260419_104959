"""
نموذج النزاعات
Dispute Model
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import (
    Column, DateTime, ForeignKey, Index,
    JSON, String, Text
)
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import UUID

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


class DisputeStatus:
    OPENED = "opened"
    UNDER_REVIEW = "under_review"
    AWAITING_EVIDENCE = "awaiting_evidence"
    MEDIATION = "mediation"
    RESOLVED_BUYER = "resolved_buyer"
    RESOLVED_SELLER = "resolved_seller"
    RESOLVED_SPLIT = "resolved_split"
    CLOSED = "closed"
    APPEALED = "appealed"


class DisputeReasonCategory:
    QUALITY = "quality"
    COMMUNICATION = "communication"
    DELIVERY = "delivery"
    PAYMENT = "payment"
    MISREPRESENTATION = "misrepresentation"
    OTHER = "other"


class DisputeResolutionType:
    FULL_REFUND = "full_refund"
    PARTIAL_REFUND = "partial_refund"
    RELEASE_FUNDS = "release_funds"
    SPLIT = "split"
    OTHER = "other"


class Dispute(BaseModel):
    """نموذج النزاع"""
    
    __tablename__ = "disputes"
    
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('deals.id'),
        nullable=False
    )
    
    opened_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False
    )
    
    resolved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True
    )
    
    deal = relationship('Deal', foreign_keys=[deal_id])
    opened_by = relationship('User', foreign_keys=[opened_by_id])
    resolved_by = relationship('User', foreign_keys=[resolved_by_id])
    
    dispute_uuid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )
    
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reason_category: Mapped[str] = mapped_column(String(50), default=DisputeReasonCategory.OTHER, nullable=False)
    
    evidence: Mapped[Optional[List[Dict]]] = mapped_column(JSON, nullable=True, default=list)
    
    status: Mapped[str] = mapped_column(String(30), default=DisputeStatus.OPENED, nullable=False)
    
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    appealed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    appeal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    extra_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    
    __table_args__ = (
        Index('ix_disputes_dispute_uuid', 'dispute_uuid'),
        Index('ix_disputes_deal_id', 'deal_id'),
        Index('ix_disputes_opened_by_id', 'opened_by_id'),
        Index('ix_disputes_status', 'status'),
        Index('ix_disputes_reason_category', 'reason_category'),
        Index('ix_disputes_created_at', 'created_at'),
        Index('ix_disputes_deadline', 'deadline'),
    )
    
    @hybrid_property
    def is_active(self) -> bool:
        return self.status in [DisputeStatus.OPENED, DisputeStatus.UNDER_REVIEW, DisputeStatus.AWAITING_EVIDENCE, DisputeStatus.MEDIATION]
    
    @hybrid_property
    def is_resolved(self) -> bool:
        return self.status in [DisputeStatus.RESOLVED_BUYER, DisputeStatus.RESOLVED_SELLER, DisputeStatus.RESOLVED_SPLIT]
    
    def set_deadline(self, hours: int = 72) -> None:
        self.deadline = utc_now() + timedelta(hours=hours)
    
    def add_evidence(self, evidence_type: str, url: str, description: str = None, added_by: str = None) -> str:
        if self.evidence is None:
            self.evidence = []
        evidence_id = str(uuid.uuid4())[:8]
        self.evidence.append({
            'id': evidence_id, 'type': evidence_type, 'url': url,
            'description': description, 'added_at': utc_now().isoformat(), 'added_by': added_by
        })
        return evidence_id
    
    def remove_evidence(self, evidence_id: str) -> bool:
        if not self.evidence:
            return False
        for i, ev in enumerate(self.evidence):
            if ev.get('id') == evidence_id:
                del self.evidence[i]
                return True
        return False
    
    def resolve(self, resolution: str, resolution_type: str, resolved_by_id: uuid.UUID, notes: str = None) -> None:
        self.resolution = resolution
        self.resolution_type = resolution_type
        self.resolved_by_id = resolved_by_id
        self.resolution_notes = notes
        self.resolved_at = utc_now()
        if resolution_type == DisputeResolutionType.FULL_REFUND:
            self.status = DisputeStatus.RESOLVED_BUYER
        elif resolution_type == DisputeResolutionType.RELEASE_FUNDS:
            self.status = DisputeStatus.RESOLVED_SELLER
        else:
            self.status = DisputeStatus.RESOLVED_BUYER
    
    def appeal(self, reason: str) -> bool:
        if not self.is_resolved:
            return False
        if self.appealed_at:
            return False
        self.status = DisputeStatus.APPEALED
        self.appealed_at = utc_now()
        self.appeal_reason = reason
        return True
    
    def close(self) -> None:
        self.status = DisputeStatus.CLOSED
    
    @classmethod
    def can_open_dispute(cls, session, deal_id: uuid.UUID, user_id: uuid.UUID) -> Tuple[bool, str]:
        from src.app.models.deal import Deal
        deal = session.get(Deal, deal_id)
        if not deal:
            return False, "Deal not found"
        if user_id not in [deal.seller_id, deal.buyer_id]:
            return False, "User not a participant"
        if deal.status not in ["funded", "in_progress", "delivered"]:
            return False, f"Deal status '{deal.status}' cannot be disputed"
        existing = session.query(cls).filter(
            cls.deal_id == deal_id,
            cls.status.in_([DisputeStatus.OPENED, DisputeStatus.UNDER_REVIEW, DisputeStatus.AWAITING_EVIDENCE, DisputeStatus.MEDIATION, DisputeStatus.APPEALED])
        ).first()
        if existing:
            return False, "Active dispute already exists"
        return True, "OK"
    
    @classmethod
    def open_dispute(cls, session, deal_id: uuid.UUID, opened_by_id: uuid.UUID, reason: str, reason_category: str = DisputeReasonCategory.OTHER) -> Optional['Dispute']:
        can_open, msg = cls.can_open_dispute(session, deal_id, opened_by_id)
        if not can_open:
            return None
        dispute = cls(deal_id=deal_id, opened_by_id=opened_by_id, reason=reason, reason_category=reason_category)
        dispute.set_deadline(72)
        session.add(dispute)
        return dispute
    
    def to_dict(self, include_sensitive: bool = False) -> Dict:
        data = {
            'id': str(self.id), 'dispute_uuid': self.dispute_uuid,
            'deal_id': str(self.deal_id), 'opened_by_id': str(self.opened_by_id),
            'reason': self.reason, 'reason_category': self.reason_category,
            'status': self.status, 'is_active': self.is_active, 'is_resolved': self.is_resolved,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data.update({'evidence': self.evidence, 'resolution_notes': self.resolution_notes})
        return data


__all__ = ["Dispute", "DisputeStatus", "DisputeReasonCategory", "DisputeResolutionType"]

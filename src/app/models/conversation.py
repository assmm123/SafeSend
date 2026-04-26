"""
نموذج المحادثة - Conversation Model
حسب وثيقة 1 - Core Foundation
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime, ForeignKey, Index, String
)
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


class ConversationStatus:
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Conversation(BaseModel):
    __tablename__ = "conversations"
    
    # معرفات بدون ForeignKey لتجنب مشاكل التوافق
    deal_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    buyer_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id'), nullable=False)
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id'), nullable=False)
    
    # علاقات أحادية الاتجاه (القاعدة 3)
    buyer = relationship('User', foreign_keys=[buyer_id])
    seller = relationship('User', foreign_keys=[seller_id])
    
    subject: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ConversationStatus.ACTIVE, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('ix_conversations_deal_id', 'deal_id'),
        Index('ix_conversations_buyer_id', 'buyer_id'),
        Index('ix_conversations_seller_id', 'seller_id'),
        Index('ix_conversations_status', 'status'),
        Index('ix_conversations_deleted_at', 'deleted_at'),
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    @property
    def is_active(self) -> bool:
        return self.status == ConversationStatus.ACTIVE and not self.is_deleted
    
    def soft_delete(self) -> None:
        self.deleted_at = utc_now()
        self.status = ConversationStatus.DELETED
    
    def restore(self) -> None:
        self.deleted_at = None
        self.status = ConversationStatus.ACTIVE
    
    def is_participant(self, user_id: str) -> bool:
        return user_id in [self.buyer_id, self.seller_id]
    
    def get_other_participant(self, user_id: str) -> Optional[str]:
        if user_id == self.buyer_id:
            return self.seller_id
        elif user_id == self.seller_id:
            return self.buyer_id
        return None
    
    def update_last_message(self) -> None:
        self.last_message_at = utc_now()
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "deal_id": self.deal_id,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "subject": self.subject,
            "status": self.status,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<Conversation id={self.id}>"


__all__ = ["Conversation", "ConversationStatus"]

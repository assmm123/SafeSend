"""
نموذج الرسائل
Message Model

يمثل الرسائل المتبادلة داخل المحادثات
حسب وثيقة 1 - Core Foundation
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, String, Text, JSON
)
from sqlalchemy.orm import Mapped, Session, relationship, mapped_column

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


class MessageType:
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    SYSTEM = "system"


class DeliveryStatus:
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"


class Message(BaseModel):
    __tablename__ = "messages"
    
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey('conversations.id'), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id'), nullable=False)
    reply_to_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('messages.id'), nullable=True)
    
    conversation = relationship('Conversation', foreign_keys=[conversation_id])
    sender = relationship('User', foreign_keys=[sender_id])
    reply_to = relationship('Message', foreign_keys=[reply_to_id], remote_side='Message.id')
    
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(20), default=MessageType.TEXT, nullable=False)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    media_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(20), default=DeliveryStatus.SENT, nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    reactions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    __table_args__ = (
        Index('ix_messages_conversation_id', 'conversation_id'),
        Index('ix_messages_sender_id', 'sender_id'),
        Index('ix_messages_is_read', 'is_read'),
        Index('ix_messages_deleted_at', 'deleted_at'),
        Index('ix_messages_created_at', 'created_at'),
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    @property
    def is_media(self) -> bool:
        return self.content_type in [MessageType.IMAGE, MessageType.VIDEO, MessageType.FILE]
    
    def mark_as_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.read_at = utc_now()
            self.delivery_status = DeliveryStatus.READ
    
    def mark_as_delivered(self) -> None:
        if self.delivery_status == DeliveryStatus.SENT:
            self.delivery_status = DeliveryStatus.DELIVERED
            self.delivered_at = utc_now()
    
    def edit(self, new_content: str) -> None:
        self.content = new_content
        self.is_edited = True
        self.edited_at = utc_now()
    
    def soft_delete(self) -> None:
        self.deleted_at = utc_now()
    
    def restore(self) -> None:
        self.deleted_at = None
    
    def add_reaction(self, user_id: str, emoji: str) -> None:
        if self.reactions is None:
            self.reactions = {}
        if emoji not in self.reactions:
            self.reactions[emoji] = []
        if user_id not in self.reactions[emoji]:
            self.reactions[emoji].append(user_id)
    
    def remove_reaction(self, user_id: str, emoji: str) -> None:
        if self.reactions and emoji in self.reactions:
            if user_id in self.reactions[emoji]:
                self.reactions[emoji].remove(user_id)
    
    def get_preview(self, max_length: int = 100) -> str:
        if self.is_deleted:
            return "[Deleted]"
        if self.content_type == MessageType.TEXT and self.content:
            return self.content[:max_length] + ("..." if len(self.content) > max_length else "")
        return self.content_type.capitalize()
    
    @classmethod
    def get_unread_count(cls, session: Session, conversation_id: str, user_id: str) -> int:
        return session.query(cls).filter(
            cls.conversation_id == conversation_id,
            cls.sender_id != user_id,
            cls.is_read == False,
            cls.deleted_at == None
        ).count()
    
    @classmethod
    def get_last_message(cls, session: Session, conversation_id: str) -> Optional['Message']:
        return session.query(cls).filter(
            cls.conversation_id == conversation_id,
            cls.deleted_at == None
        ).order_by(cls.created_at.desc()).first()
    
    def to_dict(self) -> dict:
        if self.is_deleted:
            return {"id": str(self.id), "is_deleted": True}
        return {
            "id": str(self.id), "conversation_id": self.conversation_id,
            "sender_id": self.sender_id, "content": self.content,
            "content_type": self.content_type, "media_url": self.media_url,
            "is_read": self.is_read, "delivery_status": self.delivery_status,
            "is_edited": self.is_edited, "reply_to_id": self.reply_to_id,
            "reactions": self.reactions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<Message id={self.id} sender={self.sender_id}>"


__all__ = ["Message", "MessageType", "DeliveryStatus"]

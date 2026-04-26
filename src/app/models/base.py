"""
الصنف الأساسي لجميع نماذج قاعدة البيانات
Base Model for all Database Models
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """الصنف الأساسي الإعلاني"""
    pass


class BaseModel(Base):
    """
    الصنف الأساسي لجميع النماذج
    Base Model Class for all Models
    """
    
    __abstract__ = True
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل النموذج إلى قاموس"""
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
    
    def save(self, session) -> None:
        """حفظ النموذج في قاعدة البيانات"""
        session.add(self)
    
    def delete(self, session) -> None:
        """حذف النموذج من قاعدة البيانات"""
        session.delete(self)
    
    def update(self, session, **kwargs: Any) -> None:
        """تحديث حقول النموذج"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


__all__ = ["Base", "BaseModel"]

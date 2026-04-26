"""
نموذج سجل التدقيق
Audit Log Model

يسجل جميع الإجراءات المهمة مع تطهير البيانات الحساسة
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String, Text, Integer
from sqlalchemy.orm import Mapped, Session, relationship, mapped_column
from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


# الثوابت
class AuditAction:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"


class AuditSeverity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AuditResource:
    USER = "user"
    SYSTEM = "system"


SENSITIVE_FIELDS = {"password", "password_hash", "token", "secret", "api_key"}


def sanitize_data(data: Any) -> Any:
    """تطهير البيانات الحساسة"""
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: "***REDACTED***" if k.lower() in SENSITIVE_FIELDS else sanitize_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_data(x) for x in data[:10]] + (["..."] if len(data) > 10 else [])
    if isinstance(data, str) and len(data) > 100:
        return data[:100] + "..."
    return data


class AuditLog(BaseModel):
    """نموذج سجل التدقيق"""
    __tablename__ = "audit_logs"
    
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    user = relationship('User')
    
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default=AuditSeverity.INFO, nullable=False)
    
    __table_args__ = (
        Index('ix_audit_logs_user_id', 'user_id'),
        Index('ix_audit_logs_action', 'action'),
        Index('ix_audit_logs_created_at', 'created_at'),
    )


class AuditLogger:
    """مدير سجل التدقيق"""
    
    @staticmethod
    def log(session: Session, action: str, resource: str, user_id: Optional[str] = None,
            resource_id: Optional[str] = None, old_value: Any = None, new_value: Any = None,
            ip_address: Optional[str] = None, severity: str = AuditSeverity.INFO) -> AuditLog:
        
        log_entry = AuditLog(
            user_id=user_id, action=action, resource=resource, resource_id=resource_id,
            old_value=sanitize_data(old_value), new_value=sanitize_data(new_value),
            ip_address=ip_address, severity=severity
        )
        session.add(log_entry)
        session.flush()
        return log_entry
    
    @staticmethod
    def get_for_user(session: Session, user_id: str, limit: int = 100) -> List[AuditLog]:
        return session.query(AuditLog).filter(AuditLog.user_id == user_id).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_for_resource(session: Session, resource: str, resource_id: str) -> List[AuditLog]:
        return session.query(AuditLog).filter(AuditLog.resource == resource, AuditLog.resource_id == resource_id).all()


__all__ = ["AuditLog", "AuditLogger", "AuditAction", "AuditSeverity", "AuditResource", "sanitize_data"]

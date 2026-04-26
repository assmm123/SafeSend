"""
نموذج الملفات المتقدم
Advanced File Model

يمثل الملفات المرفوعة في النظام مع دعم:
- تشفير AES-256-GCM
- فحص فيروسات ClamAV
- علامة مائية
- حذف ناعم
- تتبع التحميلات
- انتهاء صلاحية
- فهارس متقدمة
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Index,
    Integer, JSON, String, Text
)
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


class FileType:
    """أنواع الملفات"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    OTHER = "other"


class VirusScanResult:
    """نتائج فحص الفيروسات"""
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"
    SKIPPED = "skipped"
    PENDING = "pending"


class FileStatus:
    """حالات الملف"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    EXPIRED = "expired"
    DELETED = "deleted"


class File(BaseModel):
    """
    نموذج الملف المتقدم
    Advanced File Model
    """
    
    __tablename__ = "files"
    
    # ============================================
    # العلاقات
    # ============================================
    
    deal_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey('deals.id', ondelete='SET NULL'),
        nullable=True,
        index=False
    )
    
    uploader_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='RESTRICT'),
        nullable=False,
        index=False
    )
    
    last_download_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    deleted_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # علاقات أحادية الاتجاه (القاعدة 3)
    deal = relationship('Deal', foreign_keys=[deal_id])
    uploader = relationship('User', foreign_keys=[uploader_id])
    last_downloader = relationship('User', foreign_keys=[last_download_by])
    deleter = relationship('User', foreign_keys=[deleted_by])
    
    # ============================================
    # معلومات أساسية
    # ============================================
    
    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="الاسم الأصلي للملف"
    )
    
    stored_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="الاسم المخزن في النظام"
    )
    
    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="المسار الكامل للملف"
    )
    
    encrypted_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        doc="مسار النسخة المشفرة"
    )
    
    watermarked_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        doc="مسار النسخة المعلمة"
    )
    
    thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        doc="مسار الصورة المصغرة"
    )
    
    # ============================================
    # خصائص الملف
    # ============================================
    
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        doc="الحجم بالبايت"
    )
    
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="نوع MIME"
    )
    
    extension: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="الامتداد"
    )
    
    # ============================================
    # الأمان والتحقق
    # ============================================
    
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA256 للملف الأصلي"
    )
    
    encrypted_checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA256 للملف المشفر"
    )
    
    encrypted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=False,
        doc="هل تم تشفيره"
    )
    
    virus_scanned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=False,
        doc="هل تم فحصه"
    )
    
    virus_scan_result: Mapped[str] = mapped_column(
        String(50),
        default=VirusScanResult.PENDING,
        nullable=False,
        index=False,
        doc="نتيجة الفحص"
    )
    
    virus_scan_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="وقت الفحص"
    )
    
    virus_signature: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="توقيع الفيروس"
    )
    
    watermarked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=False,
        doc="هل عليه علامة مائية"
    )
    
    watermark_text: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="نص العلامة المائية"
    )
    
    # ============================================
    # الحالة
    # ============================================
    
    status: Mapped[str] = mapped_column(
        String(20),
        default=FileStatus.UPLOADING,
        nullable=False,
        doc="حالة الملف"
    )
    
    # ============================================
    # الإحصائيات
    # ============================================
    
    download_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="عدد التحميلات"
    )
    
    last_download_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="آخر تحميل"
    )
    
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="عدد المشاهدات"
    )
    
    # ============================================
    # الصلاحية
    # ============================================
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=False,
        doc="تاريخ انتهاء الصلاحية"
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=False,
        doc="تاريخ الحذف"
    )
    
    delete_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="سبب الحذف"
    )
    
    # ============================================
    # بيانات إضافية
    # ============================================
    
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="بيانات إضافية مرنة"
    )
    
    # ============================================
    # الفهارس - حسب القاعدة 1
    # ============================================
    
    __table_args__ = (
        Index('ix_files_deal_id', 'deal_id'),
        Index('ix_files_uploader_id', 'uploader_id'),
        Index('ix_files_checksum', 'checksum'),
        Index('ix_files_virus_scanned', 'virus_scanned'),
        Index('ix_files_virus_scan_result', 'virus_scan_result'),
        Index('ix_files_status', 'status'),
        Index('ix_files_expires_at', 'expires_at'),
        Index('ix_files_deleted_at', 'deleted_at'),
        Index('ix_files_encrypted', 'encrypted'),
        Index('ix_files_watermarked', 'watermarked'),
        Index('ix_files_created_at', 'created_at'),
    )
    
    # ============================================
    # الخصائص - Properties
    # ============================================
    
    @hybrid_property
    def is_deleted(self) -> bool:
        """هل الملف محذوف"""
        return self.deleted_at is not None
    
    @hybrid_property
    def is_expired(self) -> bool:
        """هل انتهت صلاحية الملف"""
        if self.expires_at is None:
            return False
        return utc_now() > self.expires_at
    
    @hybrid_property
    def is_virus_clean(self) -> bool:
        """هل الملف نظيف من الفيروسات"""
        return self.virus_scan_result == VirusScanResult.CLEAN
    
    @hybrid_property
    def is_downloadable(self) -> bool:
        """هل يمكن تحميل الملف"""
        return (
            self.status == FileStatus.READY and
            not self.is_deleted and
            not self.is_expired and
            self.is_virus_clean
        )
    
    @property
    def file_type(self) -> str:
        """نوع الملف"""
        if self.mime_type.startswith('image/'):
            return FileType.IMAGE
        elif self.mime_type.startswith('video/'):
            return FileType.VIDEO
        elif self.mime_type.startswith('audio/'):
            return FileType.AUDIO
        elif self.mime_type == 'application/pdf':
            return FileType.DOCUMENT
        elif self.mime_type in ['application/zip', 'application/x-tar', 'application/gzip']:
            return FileType.ARCHIVE
        return FileType.OTHER
    
    @property
    def size_human(self) -> str:
        """حجم الملف بصيغة مقروءة"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    @property
    def active_path(self) -> str:
        """المسار النشط للملف"""
        if self.watermarked and self.watermarked_path:
            return self.watermarked_path
        if self.encrypted and self.encrypted_path:
            return self.encrypted_path
        return self.file_path
    
    @property
    def age_days(self) -> int:
        """عمر الملف بالأيام"""
        if self.created_at is None:
            return 0
        if self.created_at.tzinfo is None:
            created = self.created_at.replace(tzinfo=timezone.utc)
        else:
            created = self.created_at
        return (utc_now() - created).days
    
    # ============================================
    # دوال - Methods
    # ============================================
    
    def mark_ready(self) -> None:
        """تعليم الملف كجاهز"""
        self.status = FileStatus.READY
    
    def mark_processing(self) -> None:
        """تعليم الملف قيد المعالجة"""
        self.status = FileStatus.PROCESSING
    
    def increment_download(self, user_id: Optional[str] = None) -> None:
        """زيادة عداد التحميل"""
        self.download_count += 1
        self.last_download_at = utc_now()
        if user_id:
            self.last_download_by = user_id
    
    def increment_view(self) -> None:
        """زيادة عداد المشاهدة"""
        self.view_count += 1
    
    def soft_delete(self, user_id: Optional[str] = None, reason: Optional[str] = None) -> None:
        """حذف ناعم"""
        self.status = FileStatus.DELETED
        self.deleted_at = utc_now()
        if user_id:
            self.deleted_by = user_id
        if reason:
            self.delete_reason = reason
    
    def restore(self) -> None:
        """استعادة الملف"""
        self.status = FileStatus.READY
        self.deleted_at = None
        self.deleted_by = None
        self.delete_reason = None
    
    def mark_virus_scanned(self, result: str, signature: Optional[str] = None) -> None:
        """تعليم نتيجة فحص الفيروسات"""
        self.virus_scanned = True
        self.virus_scan_result = result
        self.virus_scan_at = utc_now()
        if signature:
            self.virus_signature = signature
    
    def set_encrypted(self, encrypted_path: str, encrypted_checksum: str) -> None:
        """تعليم الملف كمشفر"""
        self.encrypted = True
        self.encrypted_path = encrypted_path
        self.encrypted_checksum = encrypted_checksum
    
    def set_watermarked(self, watermarked_path: str, watermark_text: str) -> None:
        """تعليم الملف كمعلم"""
        self.watermarked = True
        self.watermarked_path = watermarked_path
        self.watermark_text = watermark_text
    
    def set_thumbnail(self, thumbnail_path: str) -> None:
        """تعيين الصورة المصغرة"""
        self.thumbnail_path = thumbnail_path
    
    def set_expiry(self, days: int = 30) -> None:
        """تعيين تاريخ انتهاء الصلاحية"""
        self.expires_at = utc_now() + timedelta(days=days)
    
    def get_download_url(self, ttl: int = 300) -> str:
        """توليد رابط تحميل مؤقت"""
        return f"/api/v1/files/{self.id}/download?token={self._generate_token(ttl)}"
    
    def _generate_token(self, ttl: int) -> str:
        """توليد token تحميل"""
        import hashlib
        import time
        data = f"{self.id}:{self.checksum}:{time.time()}:{ttl}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        data = {
            'id': str(self.id),
            'deal_id': self.deal_id,
            'uploader_id': self.uploader_id,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'size_human': self.size_human,
            'mime_type': self.mime_type,
            'extension': self.extension,
            'file_type': self.file_type,
            'status': self.status,
            'encrypted': self.encrypted,
            'virus_scanned': self.virus_scanned,
            'virus_clean': self.is_virus_clean,
            'watermarked': self.watermarked,
            'download_count': self.download_count,
            'view_count': self.view_count,
            'is_downloadable': self.is_downloadable,
            'is_expired': self.is_expired,
            'is_deleted': self.is_deleted,
            'age_days': self.age_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
        
        if include_sensitive:
            data.update({
                'file_path': self.file_path,
                'checksum': self.checksum,
                'virus_scan_result': self.virus_scan_result,
                'watermark_text': self.watermark_text,
                'extra_data': self.extra_data,
            })
        
        if self.thumbnail_path:
            data['thumbnail_url'] = f"/api/v1/files/{self.id}/thumbnail"
        
        return data
    
    def __repr__(self) -> str:
        return f"<File id={self.id} name={self.original_name} status={self.status}>"


__all__ = [
    "File",
    "FileType",
    "VirusScanResult",
    "FileStatus",
]

"""
نموذج المعاملات المالية المتقدم
Advanced Transaction Model

يمثل جميع المعاملات على البلوكشين:
- إيداعات الضمان
- مدفوعات صادرة
- مستردات
- رسوم المنصة
- دعم Idempotency Keys
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey, Index,
    Integer, JSON, Numeric, String, Text
)
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

from src.app.models.base import BaseModel
from src.app.models.helpers import utc_now


class TransactionType:
    """أنواع المعاملات"""
    ESCROW_DEPOSIT = "escrow_deposit"
    PAYOUT = "payout"
    REFUND = "refund"
    FEE_COLLECTION = "fee_collection"
    GAS_FEE = "gas_fee"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class TransactionStatus:
    """حالات المعاملة"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TransactionNetwork:
    """شبكات البلوكشين"""
    TRON_MAINNET = "tron_mainnet"
    TRON_SHASTA = "tron_shasta"
    TRON_NILE = "tron_nile"


class Transaction(BaseModel):
    """
    نموذج المعاملة المتقدم
    Advanced Transaction Model
    """
    
    __tablename__ = "transactions"
    
    # ============================================
    # العلاقات
    # ============================================
    
    deal_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey('deals.id', ondelete='SET NULL'),
        nullable=True,
        index=False
    )
    
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=False
    )
    
    # علاقات أحادية الاتجاه (القاعدة 3)
    deal = relationship('Deal', foreign_keys=[deal_id])
    user = relationship('User', foreign_keys=[user_id])
    
    # ============================================
    # Idempotency (قاعدة إلزامية)
    # ============================================
    
    transaction_uuid: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=False,
        doc="معرف فريد لمنع تكرار المعاملة"
    )
    
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        doc="مفتاح Idempotency خارجي"
    )
    
    # ============================================
    # نوع المعاملة
    # ============================================
    
    tx_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=False,
        doc="نوع المعاملة"
    )
    
    network: Mapped[str] = mapped_column(
        String(20),
        default=TransactionNetwork.TRON_MAINNET,
        nullable=False,
        doc="شبكة البلوكشين"
    )
    
    # ============================================
    # بيانات البلوكشين
    # ============================================
    
    tx_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=False,
        doc="تجزئة المعاملة"
    )
    
    from_address: Mapped[Optional[str]] = mapped_column(
        String(42),
        nullable=True,
        doc="عنوان المرسل"
    )
    
    to_address: Mapped[Optional[str]] = mapped_column(
        String(42),
        nullable=True,
        doc="عنوان المستلم"
    )
    
    # ============================================
    # المبالغ
    # ============================================
    
    amount_usdt: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0"),
        doc="المبلغ بـ USDT"
    )
    
    amount_trx: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        default=Decimal("0"),
        doc="المبلغ بـ TRX"
    )
    
    fee_trx: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        default=Decimal("0"),
        doc="رسوم المعاملة بـ TRX"
    )
    
    # ============================================
    # الحالة
    # ============================================
    
    status: Mapped[str] = mapped_column(
        String(20),
        default=TransactionStatus.PENDING,
        nullable=False,
        index=False,
        doc="حالة المعاملة"
    )
    
    # ============================================
    # التأكيدات
    # ============================================
    
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="وقت التأكيد"
    )
    
    block_number: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        doc="رقم الكتلة"
    )
    
    block_confirmations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="عدد التأكيدات"
    )
    
    # ============================================
    # إعادة المحاولة
    # ============================================
    
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="عدد محاولات الإعادة"
    )
    
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="وقت آخر محاولة"
    )
    
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="الحد الأقصى للمحاولات"
    )
    
    # ============================================
    # معلومات إضافية
    # ============================================
    
    memo: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="مذكرة"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="رسالة الخطأ"
    )
    
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="بيانات إضافية"
    )
    
    # ============================================
    # الفهارس - حسب القاعدة 1
    # ============================================
    
    __table_args__ = (
        Index('ix_transactions_transaction_uuid', 'transaction_uuid'),
        Index('ix_transactions_idempotency_key', 'idempotency_key'),
        Index('ix_transactions_deal_id', 'deal_id'),
        Index('ix_transactions_user_id', 'user_id'),
        Index('ix_transactions_tx_hash', 'tx_hash'),
        Index('ix_transactions_status', 'status'),
        Index('ix_transactions_tx_type', 'tx_type'),
        Index('ix_transactions_network', 'network'),
        Index('ix_transactions_created_at', 'created_at'),
        Index('ix_transactions_confirmed_at', 'confirmed_at'),
    )
    
    # ============================================
    # الخصائص - Properties
    # ============================================
    
    @hybrid_property
    def is_confirmed(self) -> bool:
        """هل تم تأكيد المعاملة"""
        return self.status == TransactionStatus.CONFIRMED
    
    @hybrid_property
    def is_pending(self) -> bool:
        """هل المعاملة معلقة"""
        return self.status == TransactionStatus.PENDING
    
    @hybrid_property
    def is_failed(self) -> bool:
        """هل فشلت المعاملة"""
        return self.status == TransactionStatus.FAILED
    
    @property
    def has_sufficient_confirmations(self) -> bool:
        """هل لديها تأكيدات كافية (20+)"""
        return self.block_confirmations >= 20
    
    @property
    def masked_from_address(self) -> str:
        """عنوان المرسل المخفي"""
        return self._mask_address(self.from_address)
    
    @property
    def masked_to_address(self) -> str:
        """عنوان المستلم المخفي"""
        return self._mask_address(self.to_address)
    
    @property
    def explorer_url(self) -> str:
        """رابط المستكشف"""
        if not self.tx_hash:
            return ""
        if self.network == TransactionNetwork.TRON_MAINNET:
            return f"https://tronscan.org/#/transaction/{self.tx_hash}"
        elif self.network == TransactionNetwork.TRON_SHASTA:
            return f"https://shasta.tronscan.org/#/transaction/{self.tx_hash}"
        elif self.network == TransactionNetwork.TRON_NILE:
            return f"https://nile.tronscan.org/#/transaction/{self.tx_hash}"
        return ""
    
    @property
    def next_retry_delay(self) -> int:
        """التأخير قبل المحاولة التالية (بالثواني) - Exponential Backoff"""
        return 2 ** self.retry_count
    
    # ============================================
    # دوال - Methods
    # ============================================
    
    def _mask_address(self, address: Optional[str]) -> str:
        """إخفاء العنوان"""
        if not address or len(address) < 10:
            return "***"
        return f"{address[:6]}...{address[-4:]}"
    
    def confirm(self, block_number: int) -> None:
        """تأكيد المعاملة"""
        self.status = TransactionStatus.CONFIRMED
        self.confirmed_at = utc_now()
        self.block_number = block_number
        self.block_confirmations = 0
    
    def update_confirmations(self, current_block: int) -> None:
        """تحديث عدد التأكيدات"""
        if self.block_number:
            self.block_confirmations = max(0, current_block - self.block_number)
        if self.block_confirmations >= 20 and self.status == TransactionStatus.PENDING:
            self.status = TransactionStatus.CONFIRMED
            self.confirmed_at = utc_now()
            return
    
    def mark_processing(self) -> None:
        """تعليم كجاري المعالجة"""
        self.status = TransactionStatus.PROCESSING
    
    def mark_failed(self, error: str) -> None:
        """تعليم كفاشلة"""
        self.status = TransactionStatus.FAILED
        self.error_message = error
    
    def mark_cancelled(self, reason: Optional[str] = None) -> None:
        """تعليم كملغية"""
        self.status = TransactionStatus.CANCELLED
        if reason:
            self.error_message = reason
    
    def mark_retrying(self) -> bool:
        """تعليم كإعادة محاولة"""
        if not self.can_retry():
            return False
        self.retry_count += 1
        self.status = TransactionStatus.RETRYING
        self.last_retry_at = utc_now()
        return True
    
    def can_retry(self, max_retries: Optional[int] = None) -> bool:
        """هل يمكن إعادة المحاولة"""
        limit = max_retries if max_retries is not None else self.max_retries
        return (
            self.retry_count < limit and
            self.status in [TransactionStatus.FAILED, TransactionStatus.RETRYING, TransactionStatus.PENDING]
        )
    
    def calculate_total(self) -> Decimal:
        """حساب المبلغ الإجمالي"""
        return self.amount_usdt + self.amount_trx + self.fee_trx
    
    @classmethod
    def find_by_idempotency(cls, session, idempotency_key: str) -> Optional['Transaction']:
        """البحث عن معاملة بواسطة idempotency key"""
        return session.query(cls).filter(
            (cls.transaction_uuid == idempotency_key) |
            (cls.idempotency_key == idempotency_key)
        ).first()
    
    @classmethod
    def create_with_idempotency(
        cls,
        session,
        idempotency_key: str,
        **kwargs
    ) -> tuple['Transaction', bool]:
        """
        إنشاء معاملة مع Idempotency
        
        Returns:
            (transaction, created)
        """
        existing = cls.find_by_idempotency(session, idempotency_key)
        if existing:
            return existing, False
        
        tx = cls(
            transaction_uuid=idempotency_key,
            idempotency_key=idempotency_key,
            **kwargs
        )
        session.add(tx)
        return tx, True
    
    @classmethod
    def get_stats(cls, session, deal_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        """إحصائيات المعاملات"""
        query = session.query(cls)
        if deal_id:
            query = query.filter(cls.deal_id == deal_id)
        if user_id:
            query = query.filter(cls.user_id == user_id)
        
        return {
            'total': query.count(),
            'confirmed': query.filter(cls.status == TransactionStatus.CONFIRMED).count(),
            'pending': query.filter(cls.status == TransactionStatus.PENDING).count(),
            'failed': query.filter(cls.status == TransactionStatus.FAILED).count(),
            'total_usdt': float(query.with_entities(func.sum(cls.amount_usdt)).scalar() or 0),
            'total_trx': float(query.with_entities(func.sum(cls.amount_trx)).scalar() or 0),
            'total_fee': float(query.with_entities(func.sum(cls.fee_trx)).scalar() or 0),
        }
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        data = {
            'id': str(self.id),
            'transaction_uuid': self.transaction_uuid,
            'deal_id': self.deal_id,
            'user_id': self.user_id,
            'tx_type': self.tx_type,
            'tx_hash': self.tx_hash,
            'from_address': self.masked_from_address,
            'to_address': self.masked_to_address,
            'amount_usdt': float(self.amount_usdt),
            'amount_trx': float(self.amount_trx),
            'fee_trx': float(self.fee_trx),
            'status': self.status,
            'is_confirmed': self.is_confirmed,
            'block_confirmations': self.block_confirmations,
            'has_sufficient_confirmations': self.has_sufficient_confirmations,
            'retry_count': self.retry_count,
            'memo': self.memo,
            'explorer_url': self.explorer_url,
            'network': self.network,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
        
        if include_sensitive:
            data.update({
                'from_address': self.from_address,
                'to_address': self.to_address,
                'error_message': self.error_message,
                'extra_data': self.extra_data,
            })
        
        return data
    
    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.tx_type} status={self.status} amount={self.amount_usdt} USDT>"


__all__ = [
    "Transaction",
    "TransactionType",
    "TransactionStatus",
    "TransactionNetwork",
]

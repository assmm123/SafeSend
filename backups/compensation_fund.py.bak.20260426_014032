"""
Compensation Fund & Anti-Fraud Model - SafeSend
صندوق التعويضات ونموذج مكافحة الاحتيال - SafeSend

Collects 1% from every transaction. Protects users from fraud.
يجمع 1% من كل معاملة. يحمي المستخدمين من الاحتيال.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Numeric, JSON, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
import structlog

from src.app.models.base import BaseModel

logger = structlog.get_logger(__name__)

FUND_HOLD_HOURS = 48
FUND_MAX_DISBURSE_PCT = 50
FUND_RESERVE_PCT = 20
AUTO_FREEZE_DISPUTE_COUNT = 3
AUTO_FREEZE_DAYS = 30

class CompensationFund(BaseModel):
    """
    Compensation fund entry. Collects fees and pays out disputes.
    صندوق التعويضات. يجمع الرسوم ويدفع تعويضات النزاعات.
    """
    __tablename__ = 'compensation_fund'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey('transactions.id'), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='collected', nullable=False)
    used_for: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hold_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    transaction = relationship('Transaction', foreign_keys=[transaction_id])

    __table_args__ = (
        Index('ix_cf_transaction_id', 'transaction_id'),
        Index('ix_cf_status', 'status'),
        Index('ix_cf_hold_until', 'hold_until'),
    )

    def collect(self, amount: float) -> None:
        """
        Collect fee from a transaction and hold it.
        جمع رسوم من معاملة وتجميدها.
        """
        self.amount = amount
        self.status = 'held'
        self.hold_until = datetime.now(timezone.utc) + timedelta(hours=FUND_HOLD_HOURS)
        logger.info("fund.collected", transaction_id=self.transaction_id, amount=amount)

    def release_held(self) -> bool:
        """
        Release held funds after audit period.
        فك تجميد الأموال بعد فترة التدقيق.
        """
        if self.status != 'held':
            return False
        if self.hold_until and datetime.now(timezone.utc) < self.hold_until:
            return False
        self.status = 'collected'
        logger.info("fund.released", fund_id=self.id)
        return True

    def use_for_dispute(self, dispute_id: int, amount: float, approved_by: int) -> bool:
        """
        Use funds to compensate a dispute.
        استخدام الأموال لتعويض نزاع.
        """
        if self.status != 'collected':
            return False
        max_disburse = self.amount * (FUND_MAX_DISBURSE_PCT / 100)
        if amount > max_disburse:
            logger.warning("fund.exceeds_max", fund_id=self.id, amount=amount, max=max_disburse)
            return False
        self.status = 'used'
        self.used_for = dispute_id
        self.approved_by = approved_by
        logger.info("fund.used", fund_id=self.id, dispute_id=dispute_id, amount=amount)
        return True

    def refund_to_user(self, amount: float) -> bool:
        """
        Refund collected fee back to user.
        إعادة الرسوم للمستخدم.
        """
        if self.status not in ('collected', 'held'):
            return False
        self.status = 'refunded'
        logger.info("fund.refunded", fund_id=self.id, amount=amount)
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'amount': float(self.amount),
            'status': self.status,
            'used_for': self.used_for,
            'hold_until': self.hold_until.isoformat() if self.hold_until else None
        }

    @staticmethod
    def get_balance(session) -> float:
        """Get total available fund balance. / إجمالي رصيد الصندوق المتاح."""
        from sqlalchemy import func
        result = session.query(func.sum(CompensationFund.amount)).filter(
            CompensationFund.status == 'collected'
        ).scalar()
        return float(result or 0)

    @staticmethod
    def get_stats(session) -> Dict[str, Any]:
        """Get fund statistics. / إحصائيات الصندوق."""
        from sqlalchemy import func
        total = session.query(func.sum(CompensationFund.amount)).scalar() or 0
        used = session.query(func.sum(CompensationFund.amount)).filter(
            CompensationFund.status == 'used'
        ).scalar() or 0
        available = session.query(func.sum(CompensationFund.amount)).filter(
            CompensationFund.status == 'collected'
        ).scalar() or 0
        return {
            'total_collected': float(total),
            'total_used': float(used),
            'available': float(available),
            'reserve': float(available) * (FUND_RESERVE_PCT / 100)
        }


__all__ = ['CompensationFund', 'FUND_HOLD_HOURS', 'FUND_MAX_DISBURSE_PCT']

"""
محرك الوساطة المتقدم
Advanced Escrow Engine

يدير دورة حياة الصفقة كاملة:
- التحقق من الدفع
- حساب الرسوم
- تحرير الأموال تلقائياً
- معالجة الصفقات المنتهية والمتوقفة
- مطابقة المعاملات
- فحص الصحة والمقاييس
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from enum import Enum

from src.app.models.helpers import utc_now
from src.app.models.logging_config import get_logger
from src.core.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)


# ============================================
# Enums
# ============================================

class EscrowEvent(Enum):
    """أحداث الوساطة"""
    PAYMENT_RECEIVED = "payment_received"
    FUNDS_RELEASED = "funds_released"
    PAYOUT_SENT = "payout_sent"
    DEAL_EXPIRED = "deal_expired"
    DEAL_STALLED = "deal_stalled"
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED = "dispute_resolved"


# ============================================
# Data Classes
# ============================================

@dataclass
class PaymentVerificationResult:
    """نتيجة التحقق من الدفع"""
    verified: bool
    tx_hash: Optional[str] = None
    amount: Optional[Decimal] = None
    confirmations: int = 0
    is_sufficient: bool = False
    error: Optional[str] = None


@dataclass
class FeeCalculation:
    """حساب الرسوم"""
    amount: Decimal
    fee_percent: Decimal
    fee_amount: Decimal
    seller_amount: Decimal
    
    def to_dict(self) -> dict:
        return {
            "amount": float(self.amount),
            "fee_percent": float(self.fee_percent),
            "fee_amount": float(self.fee_amount),
            "seller_amount": float(self.seller_amount),
        }


@dataclass
class PayoutResult:
    """نتيجة عملية الدفع"""
    success: bool
    tx_hash: Optional[str] = None
    amount: Optional[Decimal] = None
    fee_trx: Optional[Decimal] = None
    error: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class ManualPayoutTask:
    """مهمة دفع يدوي"""
    task_id: str
    deal_id: str
    seller_id: str
    amount: Decimal
    payout_address: str
    status: str = "pending"
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class BatchProcessResult:
    """نتيجة معالجة دفعة"""
    processed: int
    success: int
    failed: int
    errors: List[str] = field(default_factory=list)
    deals: List[str] = field(default_factory=list)


@dataclass
class ReconciliationReport:
    """تقرير مطابقة المعاملات"""
    total: int
    matched: int
    unmatched: int
    discrepancies: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "matched": self.matched,
            "unmatched": self.unmatched,
            "discrepancies": self.discrepancies,
        }


@dataclass
class HealthStatus:
    """حالة صحة المحرك"""
    status: str
    tron_status: str
    pending_payouts: int
    stalled_deals: int
    circuit_breaker_state: str


# ============================================
# Escrow Engine
# ============================================

class EscrowEngine:
    """
    محرك الوساطة المتقدم
    Advanced Escrow Engine
    
    يدير جميع عمليات الوساطة المالية
    """
    
    def __init__(
        self,
        tron_service: Any,
        notification_service: Any = None,
        deal_repository: Any = None,
        celery_app: Any = None,
        redis_client: Any = None
    ):
        """
        تهيئة محرك الوساطة
        
        Args:
            tron_service: خدمة TRON (ITronService)
            notification_service: خدمة الإشعارات (INotificationService)
            deal_repository: مستودع الصفقات (IDealRepository)
            celery_app: تطبيق Celery للمهام الخلفية
            redis_client: عميل Redis للتخزين المؤقت
        """
        self.tron_service = tron_service
        self.notification_service = notification_service
        self.deal_repository = deal_repository
        self.celery_app = celery_app
        self.redis = redis_client
        
        self.circuit_breaker = CircuitBreaker(
            name="escrow_engine",
            failure_threshold=3,
            timeout=30.0
        )
        
        self._pending_payouts: List[str] = []
        self._payout_queue: List[ManualPayoutTask] = []
        
        # رسوم المنصة الافتراضية
        self.default_fee_percent = Decimal("1.0")
        
        logger.info("EscrowEngine initialized")
    
    # ============================================
    # التحقق من الدفع
    # ============================================
    
    def verify_payment(self, deal: Any) -> PaymentVerificationResult:
        """
        التحقق من وصول الدفعة للصفقة
        
        Args:
            deal: الصفقة (EscrowDeal)
            
        Returns:
            PaymentVerificationResult: نتيجة التحقق
        """
        try:
            result = self.tron_service.check_incoming_transaction(
                expected_address=deal.escrow_address,
                expected_amount=deal.amount,
                memo=deal.payment_memo
            )
            
            if result is None:
                return PaymentVerificationResult(
                    verified=False,
                    error="No transaction found"
                )
            
            # استخراج البيانات من النتيجة (تدعم dict أو object)
            if isinstance(result, dict):
                tx_hash = result.get("tx_hash")
                amount = result.get("amount", Decimal(0))
                confirmations = result.get("confirmations", 0)
                is_sufficient = amount >= deal.amount
            else:
                tx_hash = getattr(result, "tx_hash", None)
                amount = getattr(result, "amount", Decimal(0))
                confirmations = getattr(result, "confirmations", 0)
                is_sufficient = getattr(result, "is_sufficient", amount >= deal.amount)
            
            verified = confirmations >= 20 and is_sufficient
            
            if not is_sufficient:
                return PaymentVerificationResult(
                    verified=False,
                    tx_hash=tx_hash,
                    amount=amount,
                    confirmations=confirmations,
                    is_sufficient=False,
                    error=f"Insufficient amount: {amount} < {deal.amount}"
                )
            
            if confirmations < 20:
                return PaymentVerificationResult(
                    verified=False,
                    tx_hash=tx_hash,
                    amount=amount,
                    confirmations=confirmations,
                    is_sufficient=True,
                    error=f"Not enough confirmations: {confirmations}/20"
                )
            
            self._log_event(deal, EscrowEvent.PAYMENT_RECEIVED, {
                "tx_hash": tx_hash,
                "amount": float(amount)
            })
            
            return PaymentVerificationResult(
                verified=True,
                tx_hash=tx_hash,
                amount=amount,
                confirmations=confirmations,
                is_sufficient=True
            )
            
        except Exception as e:
            logger.error(f"Payment verification failed for deal {getattr(deal, 'id', 'unknown')}: {e}")
            return PaymentVerificationResult(
                verified=False,
                error=str(e)
            )
    
    # ============================================
    # حساب الرسوم
    # ============================================
    
    def calculate_fee(self, amount: Decimal, fee_percent: Decimal = None) -> FeeCalculation:
        """
        حساب رسوم المنصة
        
        Args:
            amount: المبلغ الإجمالي
            fee_percent: نسبة الرسوم (يستخدم الافتراضي إذا لم يحدد)
            
        Returns:
            FeeCalculation: نتيجة الحساب
        """
        percent = fee_percent if fee_percent is not None else self.default_fee_percent
        fee_amount = amount * (percent / Decimal("100"))
        seller_amount = amount - fee_amount
        
        return FeeCalculation(
            amount=amount,
            fee_percent=percent,
            fee_amount=fee_amount,
            seller_amount=seller_amount
        )
    
    # ============================================
    # معالجة المدفوعات
    # ============================================
    
    def process_payout(self, deal: Any, idempotency_key: str) -> PayoutResult:
        """
        معالجة الدفع للبائع
        
        Args:
            deal: الصفقة
            idempotency_key: مفتاح منع التكرار
            
        Returns:
            PayoutResult: نتيجة الدفع
        """
        try:
            payout_address = getattr(deal, 'seller_payout_address', None)
            if not payout_address:
                return PayoutResult(
                    success=False,
                    error="No payout address configured",
                    idempotency_key=idempotency_key
                )
            
            seller_amount = getattr(deal, 'seller_amount', None) or deal.amount
            
            result = self.tron_service.send_payout(
                to_address=payout_address,
                amount=seller_amount,
                idempotency_key=idempotency_key
            )
            
            if isinstance(result, dict):
                success = result.get("success", False)
                tx_hash = result.get("tx_hash")
                fee_trx = result.get("fee_trx")
                error = result.get("error")
            else:
                success = getattr(result, "success", False)
                tx_hash = getattr(result, "tx_hash", None)
                fee_trx = getattr(result, "fee_trx", None)
                error = getattr(result, "error", None)
            
            if success:
                self._log_event(deal, EscrowEvent.PAYOUT_SENT, {
                    "tx_hash": tx_hash,
                    "amount": float(seller_amount)
                })
                
                # إرسال إشعار
                if self.notification_service:
                    self.notification_service.notify_payout_sent(deal)
            
            return PayoutResult(
                success=success,
                tx_hash=tx_hash,
                amount=seller_amount,
                fee_trx=fee_trx,
                error=error,
                idempotency_key=idempotency_key
            )
            
        except Exception as e:
            logger.error(f"Payout failed for deal {getattr(deal, 'id', 'unknown')}: {e}")
            return PayoutResult(
                success=False,
                error=str(e),
                idempotency_key=idempotency_key
            )
    
    def release_funds_auto(self, deal: Any) -> Optional[str]:
        """
        تحرير الأموال تلقائياً بعد اكتمال الصفقة
        
        Args:
            deal: الصفقة
            
        Returns:
            Optional[str]: tx_hash إذا نجح، None إذا فشل
        """
        if not self.validate_deal_status(deal, "delivered"):
            return None
        
        idempotency_key = f"auto_release:{deal.id}:{utc_now().timestamp()}"
        result = self.process_payout(deal, idempotency_key)
        
        return result.tx_hash if result.success else None
    
    def create_manual_payout_task(self, deal: Any) -> ManualPayoutTask:
        """
        إنشاء مهمة دفع يدوي (للمشرف)
        
        Args:
            deal: الصفقة
            
        Returns:
            ManualPayoutTask: المهمة المنشأة
        """
        import uuid
        
        task = ManualPayoutTask(
            task_id=str(uuid.uuid4()),
            deal_id=str(deal.id),
            seller_id=str(deal.seller_id),
            amount=deal.seller_amount or deal.amount,
            payout_address=deal.seller_payout_address or ""
        )
        
        self._payout_queue.append(task)
        
        # إرسال إلى Celery إذا كان متوفراً
        if self.celery_app:
            self.celery_app.send_task(
                'payment.process_payout',
                args=[str(deal.id), f"manual:{task.task_id}"]
            )
        
        logger.info(f"Manual payout task created: {task.task_id} for deal {deal.id}")
        
        return task
    
    # ============================================
    # التحقق من الصلاحية
    # ============================================
    
    def validate_deal_status(self, deal: Any, required_status: str) -> bool:
        """
        التحقق من حالة الصفقة
        
        Args:
            deal: الصفقة
            required_status: الحالة المطلوبة
            
        Returns:
            bool: True إذا كانت الحالة مطابقة
        """
        current_status = getattr(deal, 'status', None)
        return current_status == required_status
    
    # ============================================
    # معالجة الصفقات المنتهية والمتوقفة
    # ============================================
    
    def process_expired_deals(self) -> BatchProcessResult:
        """
        معالجة الصفقات المنتهية
        
        Returns:
            BatchProcessResult: نتيجة المعالجة
        """
        if not self.deal_repository:
            return BatchProcessResult(processed=0, success=0, failed=0)
        
        expired = self.deal_repository.get_expired() if hasattr(self.deal_repository, 'get_expired') else []
        processed = []
        errors = []
        
        for deal in expired:
            try:
                self._log_event(deal, EscrowEvent.DEAL_EXPIRED, {})
                processed.append(str(deal.id))
            except Exception as e:
                errors.append(str(e))
        
        return BatchProcessResult(
            processed=len(expired),
            success=len(processed),
            failed=len(expired) - len(processed),
            errors=errors,
            deals=processed
        )
    
    def process_stalled_deals(self) -> List[Any]:
        """
        معالجة الصفقات المتوقفة
        
        Returns:
            List: الصفقات المعالجة
        """
        if not self.deal_repository:
            return []
        
        stalled = []
        if hasattr(self.deal_repository, 'get_stalled'):
            stalled = self.deal_repository.get_stalled(hours=48)
        
        processed = []
        for deal in stalled:
            self._log_event(deal, EscrowEvent.DEAL_STALLED, {})
            processed.append(deal)
        
        return processed
    
    # ============================================
    # مطابقة المعاملات
    # ============================================
    
    def reconcile_transactions(self) -> ReconciliationReport:
        """
        مطابقة المعاملات مع البلوكشين
        
        Returns:
            ReconciliationReport: تقرير المطابقة
        """
        # TODO: تنفيذ المطابقة مع TronGrid
        return ReconciliationReport(
            total=0,
            matched=0,
            unmatched=0,
            discrepancies=[]
        )
    
    # ============================================
    # دوال داخلية
    # ============================================
    
    def _log_event(self, deal: Any, event: EscrowEvent, metadata: Dict[str, Any]):
        """تسجيل حدث"""
        logger.info(
            f"Escrow event: {event.value}",
            extra={
                "deal_id": str(getattr(deal, 'id', 'unknown')),
                "event": event.value,
                "metadata": metadata
            }
        )
    
    # ============================================
    # الصحة والمراقبة
    # ============================================
    
    def health_check(self) -> HealthStatus:
        """
        فحص صحة المحرك
        
        Returns:
            HealthStatus: حالة الصحة
        """
        tron_health = self.tron_service.health_check()
        
        if isinstance(tron_health, dict):
            tron_status = tron_health.get("status", "healthy")
        else:
            tron_status = getattr(tron_health, "status", "healthy")
        
        if tron_status == "unhealthy":
            status = "unhealthy"
        elif tron_status == "degraded" or self.circuit_breaker.state.value == "open":
            status = "degraded"
        else:
            status = "healthy"
        
        stalled_count = len(self.process_stalled_deals())
        
        return HealthStatus(
            status=status,
            tron_status=tron_status,
            pending_payouts=len(self._pending_payouts) + len(self._payout_queue),
            stalled_deals=stalled_count,
            circuit_breaker_state=self.circuit_breaker.state.value
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات المحرك
        
        Returns:
            Dict: إحصائيات Prometheus
        """
        return {
            "pending_payouts": len(self._pending_payouts) + len(self._payout_queue),
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "tron_network": getattr(self.tron_service, "network", "unknown"),
            "fee_percent": float(self.default_fee_percent),
        }


__all__ = [
    "EscrowEngine",
    "PaymentVerificationResult",
    "FeeCalculation",
    "PayoutResult",
    "ManualPayoutTask",
    "BatchProcessResult",
    "ReconciliationReport",
    "HealthStatus",
    "EscrowEvent",
]

# ============================================
# Compatibility Classes for __init__.py
# ============================================

class PayoutStatus:
    """حالات الدفع - للتوافق"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EscrowPayoutResult:
    """نتيجة دفع الوساطة - للتوافق"""
    def __init__(self, success: bool, tx_hash: str = None, error: str = None):
        self.success = success
        self.tx_hash = tx_hash
        self.error = error


# تحديث __all__
__all__ = [
    "EscrowEngine",
    "PaymentVerificationResult", 
    "FeeCalculation",
    "PayoutResult",
    "ManualPayoutTask",
    "BatchProcessResult",
    "ReconciliationReport",
    "HealthStatus",
    "EscrowEvent",
    "PayoutStatus",
    "EscrowPayoutResult",
]

"""
Circuit Breaker Pattern
نموذج قاطع الدائرة

يمنع استنزاف الموارد عند فشل الخدمات الخارجية
يوفر حماية للخدمات مثل TronGrid و Webhook و Virus Scanner
"""

import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional


class CircuitBreakerState(Enum):
    """حالات Circuit Breaker"""
    CLOSED = "closed"       # يعمل طبيعياً
    OPEN = "open"           # مفتوح - يرفض جميع الطلبات
    HALF_OPEN = "half_open" # نصف مفتوح - يختبر التعافي


class CircuitBreakerOpenError(Exception):
    """يرمى عندما يكون Circuit Breaker في حالة OPEN"""
    def __init__(self, name: str, timeout: float):
        self.name = name
        self.timeout = timeout
        super().__init__(f"Circuit '{name}' is OPEN. Retry after {timeout:.1f}s")


class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation
    تنفيذ نمط قاطع الدائرة
    
    يحمي الخدمات الخارجية من الحمل الزائد عند الفشل المتكرر
    
    Attributes:
        name (str): اسم القاطع
        failure_threshold (int): عدد مرات الفشل قبل الفتح
        timeout (float): مدة البقاء مفتوحاً بالثواني
        half_open_max_calls (int): عدد الطلبات المسموحة في HALF_OPEN
    """
    
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_max_calls: int = 1,
        use_exponential_backoff: bool = False
    ):
        """
        تهيئة Circuit Breaker
        
        Args:
            name (str): اسم القاطع للتعريف
            failure_threshold (int): عدد مرات الفشل قبل الفتح
            timeout (float): مدة البقاء مفتوحاً بالثواني
            half_open_max_calls (int): عدد الطلبات المسموحة في HALF_OPEN
            use_exponential_backoff (bool): استخدام تأخير متزايد
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.use_exponential_backoff = use_exponential_backoff
        
        # الحالة الحالية
        self._state = CircuitBreakerState.CLOSED
        self._lock = threading.Lock()
        
        # عدادات
        self._failure_count = 0
        self._consecutive_failures = 0
        self._success_count = 0
        self._rejected_count = 0
        self._half_open_calls = 0
        
        # وقت آخر فشل
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        
        # للـ metrics
        self._total_calls = 0
        self._total_success = 0
        self._total_failures = 0
    
    @property
    def state(self) -> CircuitBreakerState:
        """الحالة الحالية للقاطع"""
        with self._lock:
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """هل القاطع مغلق (يعمل)؟"""
        return self.state == CircuitBreakerState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """هل القاطع مفتوح (فشل)؟"""
        return self.state == CircuitBreakerState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """هل القاطع نصف مفتوح (اختبار)؟"""
        return self.state == CircuitBreakerState.OPEN
    
    def _get_timeout(self) -> float:
        """حساب مدة البقاء مفتوحاً"""
        if self.use_exponential_backoff:
            return min(self.timeout * (2 ** self._consecutive_failures), 3600)
        return self.timeout
    
    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """تغيير حالة القاطع مع تسجيل"""
        old_state = self._state
        self._state = new_state
        
        if new_state == CircuitBreakerState.OPEN:
            self._opened_at = time.time()
        
        # تسجيل التغيير
        from src.app.models.logging_config import get_logger
        logger = get_logger(__name__)
        logger.warning(
            f"Circuit '{self.name}' state changed: {old_state.value} -> {new_state.value}",
            extra={"extra_data": {
                "circuit": self.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "failure_count": self._failure_count
            }}
        )
    
    def _check_and_transition(self) -> None:
        """التحقق من حالة القاطع وتحديثها إذا لزم"""
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                # التحقق من انتهاء timeout
                if self._opened_at and (time.time() - self._opened_at) >= self._get_timeout():
                    self._transition_to(CircuitBreakerState.HALF_OPEN)
                    self._half_open_calls = 0
    
    def _on_success(self) -> None:
        """معالجة نجاح العملية"""
        with self._lock:
            self._total_calls += 1
            self._total_success += 1
            self._success_count += 1
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._half_open_calls += 1
                # إذا نجحت الطلبات المسموحة، نعود إلى CLOSED
                if self._half_open_calls >= self.half_open_max_calls:
                    self._transition_to(CircuitBreakerState.CLOSED)
                    self._failure_count = 0
                    self._consecutive_failures = 0
    
    def _on_failure(self) -> None:
        """معالجة فشل العملية"""
        with self._lock:
            self._total_calls += 1
            self._total_failures += 1
            self._failure_count += 1
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                # فشل في HALF_OPEN -> نعود إلى OPEN
                self._transition_to(CircuitBreakerState.OPEN)
            elif self._state == CircuitBreakerState.CLOSED:
                # فشل في CLOSED -> نتحقق من الوصول للحد
                if self._failure_count >= self.failure_threshold:
                    self._transition_to(CircuitBreakerState.OPEN)
    
    def _on_reject(self) -> None:
        """معالجة رفض الطلب"""
        with self._lock:
            self._rejected_count += 1
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        تنفيذ دالة مع حماية Circuit Breaker
        
        Args:
            func: الدالة المراد تنفيذها
            *args: معاملات الدالة
            **kwargs: معاملات مسماة
            
        Returns:
            نتيجة الدالة
            
        Raises:
            CircuitBreakerOpenError: إذا كان القاطع مفتوحاً
            Exception: أي استثناء من الدالة الأصلية
        """
        self._check_and_transition()
        
        with self._lock:
            current_state = self._state
        
        # إذا كان القاطع مفتوحاً، ارفض فوراً
        if current_state == CircuitBreakerState.OPEN:
            self._on_reject()
            raise CircuitBreakerOpenError(self.name, self._get_timeout())
        
        # إذا كان HALF_OPEN وتجاوزنا الحد المسموح
        if current_state == CircuitBreakerState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                self._on_reject()
                raise CircuitBreakerOpenError(self.name, self._get_timeout())
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def get_state(self) -> CircuitBreakerState:
        """الحصول على الحالة الحالية"""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات القاطع
        
        Returns:
            Dict: إحصائيات القاطع
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "rejected_count": self._rejected_count,
                "consecutive_failures": self._consecutive_failures,
                "total_calls": self._total_calls,
                "total_success": self._total_success,
                "total_failures": self._total_failures,
                "failure_threshold": self.failure_threshold,
                "timeout": self.timeout,
                "opened_at": self._opened_at,
                "last_failure_time": self._last_failure_time,
                "success_rate": (self._total_success / self._total_calls * 100) if self._total_calls > 0 else 0,
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        فحص صحة القاطع
        
        Returns:
            Dict: حالة الصحة
        """
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                status = "degraded"
                message = f"Circuit is OPEN. Opened at {self._opened_at}"
            elif self._state == CircuitBreakerState.HALF_OPEN:
                status = "degraded"
                message = "Circuit is HALF_OPEN, testing recovery"
            else:
                status = "healthy"
                message = "Circuit is CLOSED, operating normally"
            
            return {
                "status": status,
                "message": message,
                "state": self._state.value,
                "name": self.name,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
            }
    
    def reset(self) -> None:
        """إعادة تعيين القاطع إلى الحالة المغلقة"""
        with self._lock:
            self._transition_to(CircuitBreakerState.CLOSED)
            self._failure_count = 0
            self._consecutive_failures = 0
            self._half_open_calls = 0
            self._opened_at = None
            self._last_failure_time = None
    
    def __repr__(self) -> str:
        return f"<CircuitBreaker name='{self.name}' state={self._state.value}>"


# ============================================
# Circuit Breaker Registry
# ============================================

class CircuitBreakerRegistry:
    """
    سجل القواطع - لإدارة عدة قواطع في النظام
    Circuit Breaker Registry - Manage multiple breakers
    """
    
    _breakers: Dict[str, CircuitBreaker] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get(cls, name: str, **kwargs) -> CircuitBreaker:
        """
        الحصول على قاطع باسم معين (ينشئه إذا لم يوجد)
        
        Args:
            name (str): اسم القاطع
            **kwargs: معاملات إضافية لـ CircuitBreaker
            
        Returns:
            CircuitBreaker: القاطع المطلوب
        """
        with cls._lock:
            if name not in cls._breakers:
                cls._breakers[name] = CircuitBreaker(name=name, **kwargs)
            return cls._breakers[name]
    
    @classmethod
    def get_all_metrics(cls) -> Dict[str, Any]:
        """
        الحصول على إحصائيات جميع القواطع
        
        Returns:
            Dict: إحصائيات جميع القواطع
        """
        with cls._lock:
            return {
                name: breaker.get_metrics()
                for name, breaker in cls._breakers.items()
            }
    
    @classmethod
    def health_check_all(cls) -> Dict[str, Any]:
        """
        فحص صحة جميع القواطع
        
        Returns:
            Dict: حالة صحة جميع القواطع
        """
        with cls._lock:
            results = {}
            overall = "healthy"
            
            for name, breaker in cls._breakers.items():
                health = breaker.health_check()
                results[name] = health
                if health["status"] == "degraded":
                    overall = "degraded"
            
            return {
                "status": overall,
                "breakers": results,
                "total": len(cls._breakers)
            }
    
    @classmethod
    def reset_all(cls) -> None:
        """إعادة تعيين جميع القواطع"""
        with cls._lock:
            for breaker in cls._breakers.values():
                breaker.reset()
    
    @classmethod
    def list_breakers(cls) -> list:
        """قائمة بأسماء جميع القواطع"""
        with cls._lock:
            return list(cls._breakers.keys())


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerOpenError",
    "CircuitBreakerRegistry",
]

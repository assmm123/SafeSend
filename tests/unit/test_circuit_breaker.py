"""
اختبارات Circuit Breaker Pattern
Unit Tests for Circuit Breaker
"""

import sys
import os
import time
import threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)


class TestCircuitBreakerBasic:
    """اختبارات أساسية لـ Circuit Breaker"""
    
    def test_initial_state(self):
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False
    
    def test_successful_call(self):
        cb = CircuitBreaker(name="test")
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.get_metrics()["success_count"] == 1
    
    def test_failed_call_increments_failure_count(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        
        def fail_func():
            raise ValueError("Test error")
        
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail_func)
        
        metrics = cb.get_metrics()
        assert metrics["failure_count"] == 2
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_opens_after_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=2)
        
        def fail_func():
            raise ValueError("Test error")
        
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail_func)
        
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_rejects_when_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        
        def fail_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitBreakerState.OPEN
        
        def success_func():
            return "success"
        
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(success_func)
        
        metrics = cb.get_metrics()
        assert metrics["rejected_count"] == 1


class TestCircuitBreakerHalfOpen:
    """اختبارات حالة HALF_OPEN"""
    
    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout=0.1)
        
        def fail_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitBreakerState.OPEN
        
        # انتظار timeout
        time.sleep(0.15)
        
        # التحقق من الحالة (يتم التحقق عند call)
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state in [CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED]
    
    def test_closes_after_successful_half_open_calls(self):
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            timeout=0.1,
            half_open_max_calls=2
        )
        
        def fail_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        time.sleep(0.15)
        
        def success_func():
            return "success"
        
        # نجاح في HALF_OPEN
        cb.call(success_func)
        assert cb.state in [CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED]
        
        # نجاح ثاني -> العودة إلى CLOSED
        cb.call(success_func)
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_opens_again_on_failure_in_half_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout=0.1)
        
        def fail_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        time.sleep(0.15)
        
        # فشل في HALF_OPEN -> يعود إلى OPEN
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitBreakerState.OPEN


class TestCircuitBreakerMetrics:
    """اختبارات الإحصائيات"""
    
    def test_get_metrics(self):
        cb = CircuitBreaker(name="metrics_test", failure_threshold=3)
        
        def success_func():
            return "ok"
        
        def fail_func():
            raise ValueError("fail")
        
        cb.call(success_func)
        cb.call(success_func)
        
        try:
            cb.call(fail_func)
        except ValueError:
            pass
        
        metrics = cb.get_metrics()
        assert metrics["name"] == "metrics_test"
        assert metrics["total_calls"] == 3
        assert metrics["total_success"] == 2
        assert metrics["total_failures"] == 1
        assert metrics["state"] == "closed"
        assert "success_rate" in metrics
    
    def test_health_check_healthy(self):
        cb = CircuitBreaker(name="health_test")
        health = cb.health_check()
        assert health["status"] == "healthy"
        assert health["state"] == "closed"
    
    def test_health_check_degraded(self):
        cb = CircuitBreaker(name="health_test", failure_threshold=1)
        
        def fail_func():
            raise ValueError("fail")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        health = cb.health_check()
        assert health["status"] == "degraded"
        assert health["state"] == "open"


class TestCircuitBreakerReset:
    """اختبارات إعادة التعيين"""
    
    def test_reset(self):
        cb = CircuitBreaker(name="reset_test", failure_threshold=1)
        
        def fail_func():
            raise ValueError("fail")
        
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        assert cb.state == CircuitBreakerState.OPEN
        
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        
        metrics = cb.get_metrics()
        assert metrics["failure_count"] == 0


class TestCircuitBreakerRegistry:
    """اختبارات سجل القواطع"""
    
    def test_get_creates_new_breaker(self):
        CircuitBreakerRegistry.reset_all()
        cb = CircuitBreakerRegistry.get("tron_service")
        assert cb is not None
        assert cb.name == "tron_service"
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_get_returns_same_instance(self):
        CircuitBreakerRegistry.reset_all()
        cb1 = CircuitBreakerRegistry.get("webhook")
        cb2 = CircuitBreakerRegistry.get("webhook")
        assert cb1 is cb2
    
    def test_get_all_metrics(self):
        CircuitBreakerRegistry.reset_all()
        CircuitBreakerRegistry.get("service1")
        CircuitBreakerRegistry.get("service2")
        
        metrics = CircuitBreakerRegistry.get_all_metrics()
        assert "service1" in metrics
        assert "service2" in metrics
    
    def test_health_check_all(self):
        CircuitBreakerRegistry.reset_all()
        CircuitBreakerRegistry.get("healthy_service")
        
        health = CircuitBreakerRegistry.health_check_all()
        assert health["status"] == "healthy"
        assert health["total"] >= 1
    
    def test_list_breakers(self):
        CircuitBreakerRegistry.reset_all()
        CircuitBreakerRegistry.get("tron")
        CircuitBreakerRegistry.get("webhook")
        CircuitBreakerRegistry.get("virus_scanner")
        
        names = CircuitBreakerRegistry.list_breakers()
        assert "tron" in names
        assert "webhook" in names
        assert "virus_scanner" in names
        assert len(names) >= 3
    
    def test_reset_all(self):
        CircuitBreakerRegistry.reset_all()
        cb1 = CircuitBreakerRegistry.get("test1", failure_threshold=1)
        cb2 = CircuitBreakerRegistry.get("test2", failure_threshold=1)
        
        def fail_func():
            raise ValueError("fail")
        
        with pytest.raises(ValueError):
            cb1.call(fail_func)
        with pytest.raises(ValueError):
            cb2.call(fail_func)
        
        assert cb1.state == CircuitBreakerState.OPEN
        assert cb2.state == CircuitBreakerState.OPEN
        
        CircuitBreakerRegistry.reset_all()
        
        assert cb1.state == CircuitBreakerState.CLOSED
        assert cb2.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerThreadSafety:
    """اختبارات السلامة مع الخيوط المتعددة"""
    
    def test_concurrent_calls(self):
        cb = CircuitBreaker(name="thread_test", failure_threshold=10)
        results = []
        errors = []
        
        def call_breaker():
            try:
                def success_func():
                    time.sleep(0.01)
                    return "ok"
                result = cb.call(success_func)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for _ in range(20):
            t = threading.Thread(target=call_breaker)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(results) == 20
        assert len(errors) == 0
        metrics = cb.get_metrics()
        assert metrics["total_success"] == 20


class TestCircuitBreakerExponentialBackoff:
    """اختبارات التأخير المتزايد"""
    
    def test_exponential_backoff_increases_timeout(self):
        cb = CircuitBreaker(
            name="exp_test",
            failure_threshold=1,
            timeout=1.0,
            use_exponential_backoff=True
        )
        
        def fail_func():
            raise ValueError("fail")
        
        # فشل أول
        with pytest.raises(ValueError):
            cb.call(fail_func)
        
        # التحقق من أن timeout يزداد مع الفشل المتكرر
        initial_timeout = cb._get_timeout()
        
        # محاكاة فتح وإغلاق متكرر
        for i in range(3):
            time.sleep(0.01)
            cb.reset()
            with pytest.raises(ValueError):
                cb.call(fail_func)
        
        final_timeout = cb._get_timeout()
        assert final_timeout >= initial_timeout


__all__ = [
    "TestCircuitBreakerBasic",
    "TestCircuitBreakerHalfOpen",
    "TestCircuitBreakerMetrics",
    "TestCircuitBreakerReset",
    "TestCircuitBreakerRegistry",
    "TestCircuitBreakerThreadSafety",
    "TestCircuitBreakerExponentialBackoff",
]

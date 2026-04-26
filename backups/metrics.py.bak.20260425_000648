"""
Prometheus Metrics - SafeSend API
مقاييس Prometheus لواجهة SafeSend API

Tracks system performance: requests, deals, payments, errors.
يتتبع أداء النظام: الطلبات، الصفقات، المدفوعات، الأخطاء.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry, multiprocess
from flask import Flask, request, Response
from typing import Optional, Dict, Any
from functools import wraps
import time

# ============================================================
# 📊 Request Metrics
# ============================================================

request_count = Counter(
    'safesend_requests_total',
    'Total number of HTTP requests / إجمالي عدد طلبات HTTP',
    ['method', 'endpoint', 'status_code']
)

request_duration = Histogram(
    'safesend_request_duration_seconds',
    'HTTP request duration in seconds / مدة طلب HTTP بالثواني',
    ['method', 'endpoint']
)

# ============================================================
# 👤 User Metrics
# ============================================================

active_users = Gauge(
    'safesend_active_users',
    'Number of currently active users / عدد المستخدمين النشطين حالياً'
)

# ============================================================
# 📋 Deal Metrics
# ============================================================

active_deals = Gauge(
    'safesend_active_deals',
    'Number of currently active deals / عدد الصفقات النشطة حالياً'
)

deals_created = Counter(
    'safesend_deals_created_total',
    'Total number of deals created / إجمالي عدد الصفقات المنشأة'
)

deals_completed = Counter(
    'safesend_deals_completed_total',
    'Total number of deals completed / إجمالي عدد الصفقات المكتملة'
)

# ============================================================
# 💰 Payment Metrics
# ============================================================

payments_received = Counter(
    'safesend_payments_received_total',
    'Total number of payments received / إجمالي عدد المدفوعات المستلمة',
    ['currency']
)

payouts_sent = Counter(
    'safesend_payouts_sent_total',
    'Total number of payouts sent / إجمالي عدد المدفوعات المرسلة',
    ['currency']
)

# ============================================================
# ⚠️ Dispute Metrics
# ============================================================

disputes_opened = Counter(
    'safesend_disputes_opened_total',
    'Total number of disputes opened / إجمالي عدد النزاعات المفتوحة'
)

# ============================================================
# ❌ Error Metrics
# ============================================================

errors_total = Counter(
    'safesend_errors_total',
    'Total number of errors / إجمالي عدد الأخطاء',
    ['type', 'endpoint']
)

# ============================================================
# 🔗 External Service Metrics
# ============================================================

tron_api_duration = Histogram(
    'safesend_tron_api_duration_seconds',
    'Tron API request duration in seconds / مدة طلب Tron API بالثواني',
    ['operation']
)

# ============================================================
# 📁 File Metrics
# ============================================================

file_upload_size = Histogram(
    'safesend_file_upload_size_bytes',
    'File upload size in bytes / حجم الملفات المرفوعة بالبايت',
    ['mime_type']
)

# ============================================================
# 🔌 Connection Metrics
# ============================================================

websocket_connections = Gauge(
    'safesend_websocket_connections',
    'Number of active WebSocket connections / عدد اتصالات WebSocket النشطة'
)

celery_tasks_pending = Gauge(
    'safesend_celery_tasks_pending',
    'Number of pending Celery tasks / عدد مهام Celery المعلقة'
)

celery_tasks_completed = Counter(
    'safesend_celery_tasks_completed_total',
    'Total number of completed Celery tasks / إجمالي عدد مهام Celery المكتملة',
    ['task_name']
)

database_connections = Gauge(
    'safesend_database_connections',
    'Number of active database connections / عدد اتصالات قاعدة البيانات النشطة'
)

redis_connections = Gauge(
    'safesend_redis_connections',
    'Number of active Redis connections / عدد اتصالات Redis النشطة'
)

# ============================================================
# 🛠️ Setup & Helpers
# ============================================================

def setup_metrics(app: Flask) -> None:
    """
    Register Prometheus metrics endpoint on Flask app.
    تسجيل نقطة نهاية مقاييس Prometheus على تطبيق Flask.
    
    Args:
        app: Flask application instance
    """
    @app.route('/metrics')
    def metrics():
        """Expose Prometheus metrics endpoint."""
        return Response(generate_latest(), mimetype='text/plain')
    
    app.logger.info("metrics.endpoint.registered")

def increment_counter(name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
    """
    Increment a Prometheus counter by value.
    زيادة عداد Prometheus بقيمة.
    
    Args:
        name: Counter name (must match a defined Counter)
        value: Increment amount
        labels: Optional label key-value pairs
    """
    counters = {
        'request_count': request_count,
        'deals_created': deals_created,
        'deals_completed': deals_completed,
        'payments_received': payments_received,
        'payouts_sent': payouts_sent,
        'disputes_opened': disputes_opened,
        'errors_total': errors_total,
        'celery_tasks_completed': celery_tasks_completed
    }
    
    counter = counters.get(name)
    if counter and labels:
        counter.labels(**labels).inc(value)
    elif counter:
        counter.inc(value)

def observe_histogram(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """
    Observe a value in a Prometheus histogram.
    تسجيل قيمة في هيستوجرام Prometheus.
    
    Args:
        name: Histogram name
        value: Observation value
        labels: Optional label key-value pairs
    """
    histograms = {
        'request_duration': request_duration,
        'tron_api_duration': tron_api_duration,
        'file_upload_size': file_upload_size
    }
    
    histogram = histograms.get(name)
    if histogram and labels:
        histogram.labels(**labels).observe(value)
    elif histogram:
        histogram.observe(value)

def set_gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """
    Set a Prometheus gauge to value.
    تعيين قيمة مقياس Prometheus.
    
    Args:
        name: Gauge name
        value: New gauge value
        labels: Optional label key-value pairs
    """
    gauges = {
        'active_users': active_users,
        'active_deals': active_deals,
        'websocket_connections': websocket_connections,
        'celery_tasks_pending': celery_tasks_pending,
        'database_connections': database_connections,
        'redis_connections': redis_connections
    }
    
    gauge = gauges.get(name)
    if gauge and labels:
        gauge.labels(**labels).set(value)
    elif gauge:
        gauge.set(value)

def track_request_duration() -> callable:
    """
    Decorator to track HTTP request duration.
    ديكورتر لتتبع مدة طلب HTTP.
    
    Usage:
        @app.route('/api/v1/deals')
        @track_request_duration()
        def get_deals():
            ...
    """
    def decorator(f: callable) -> callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = f(*args, **kwargs)
                status_code = 200
                if isinstance(result, tuple):
                    status_code = result[1] if len(result) > 1 else 200
                request_count.labels(
                    method=request.method,
                    endpoint=request.path,
                    status_code=str(status_code)
                ).inc()
                return result
            except Exception as e:
                request_count.labels(
                    method=request.method,
                    endpoint=request.path,
                    status_code='500'
                ).inc()
                raise
            finally:
                duration = time.time() - start
                request_duration.labels(
                    method=request.method,
                    endpoint=request.path
                ).observe(duration)
        return wrapper
    return decorator

def track_function_duration(name: str) -> callable:
    """
    Decorator to track function execution duration.
    ديكورتر لتتبع مدة تنفيذ دالة.
    
    Args:
        name: Function name for histogram label
        
    Usage:
        @track_function_duration('verify_payment')
        def verify_payment(deal):
            ...
    """
    def decorator(f: callable) -> callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                return f(*args, **kwargs)
            finally:
                duration = time.time() - start
                request_duration.labels(
                    method='FUNCTION',
                    endpoint=name
                ).observe(duration)
        return wrapper
    return decorator

# ============================================================
# 📦 Export
# ============================================================

__all__ = [
    'request_count',
    'request_duration',
    'active_users',
    'active_deals',
    'deals_created',
    'deals_completed',
    'payments_received',
    'payouts_sent',
    'disputes_opened',
    'errors_total',
    'tron_api_duration',
    'file_upload_size',
    'websocket_connections',
    'celery_tasks_pending',
    'celery_tasks_completed',
    'database_connections',
    'redis_connections',
    'setup_metrics',
    'increment_counter',
    'observe_histogram',
    'set_gauge',
    'track_request_duration',
    'track_function_duration'
]

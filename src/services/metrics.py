"""
Prometheus Metrics - SafeSend
مقاييس Prometheus - SafeSend

Exposes application metrics for monitoring.
يعرض مقاييس التطبيق للمراقبة.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from flask import Blueprint, Response, request
import time
from functools import wraps
import structlog

logger = structlog.get_logger(__name__)

metrics_bp = Blueprint('metrics_v1', __name__, url_prefix='/api/v1/metrics')

# ============================================
# Metrics Definitions
# ============================================

# Request metrics
request_count = Counter(
    'safesend_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_latency = Histogram(
    'safesend_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

# Business metrics
active_users = Gauge(
    'safesend_active_users',
    'Number of active users'
)

active_deals = Gauge(
    'safesend_active_deals',
    'Number of active deals'
)

total_volume_usdt = Gauge(
    'safesend_total_volume_usdt',
    'Total transaction volume in USDT'
)

disputes_open = Gauge(
    'safesend_disputes_open',
    'Number of open disputes'
)

payments_pending = Gauge(
    'safesend_payments_pending',
    'Number of pending payments'
)

# Authentication metrics
login_attempts = Counter(
    'safesend_login_attempts_total',
    'Total login attempts',
    ['result']
)

registrations = Counter(
    'safesend_registrations_total',
    'Total user registrations'
)

# 2FA metrics
two_fa_enabled = Gauge(
    'safesend_2fa_enabled',
    'Number of users with 2FA enabled'
)

# File metrics
files_uploaded = Counter(
    'safesend_files_uploaded_total',
    'Total files uploaded'
)

total_file_size = Gauge(
    'safesend_total_file_size_bytes',
    'Total file size in bytes'
)


# ============================================
# Metrics Endpoint
# ============================================

@metrics_bp.route('', methods=['GET'])
def metrics():
    """
    Expose Prometheus metrics.
    عرض مقاييس Prometheus.
    """
    # Update business metrics from database
    try:
        from src.app.models.database import get_db
        from src.app.models.user import User
        from src.app.models.deal import Deal
        from src.app.models.dispute import Dispute
        from src.app.models.transaction import Transaction
        from src.app.models.file import File
        
        db = next(get_db())
        
        active_users.set(db.query(User).filter(User.is_active == True).count())
        two_fa_enabled.set(db.query(User).filter(User.is_2fa_enabled == True).count())
        active_deals.set(db.query(Deal).filter(Deal.status.in_(['active', 'in_progress'])).count())
        disputes_open.set(db.query(Dispute).filter(Dispute.status.in_(['opened', 'pending', 'in_review'])).count())
        payments_pending.set(db.query(Transaction).filter(Transaction.status == 'pending').count())
        
        # Total volume
        txs = db.query(Transaction).filter(Transaction.status == 'confirmed').all()
        volume = sum(float(t.amount_usdt or 0) for t in txs)
        total_volume_usdt.set(volume)
        
        # File stats
        all_files = db.query(File).all()
        files_uploaded.inc(len(all_files))
        total_file_size.set(sum(f.file_size or 0 for f in all_files))
        
        db.close()
    except Exception as e:
        logger.warning("metrics.update_failed", error=str(e))
    
    return Response(generate_latest(REGISTRY), mimetype='text/plain')


# ============================================
# Decorator for tracking request metrics
# ============================================

def track_request_metrics():
    """Decorator factory for tracking request metrics."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            start = time.time()
            method = request.method
            endpoint = request.endpoint or 'unknown'
            
            try:
                response = f(*args, **kwargs)
                status = getattr(response, 'status_code', 200)
                request_count.labels(method=method, endpoint=endpoint, status=str(status)).inc()
                request_latency.labels(method=method, endpoint=endpoint).observe(time.time() - start)
                return response
            except Exception:
                request_count.labels(method=method, endpoint=endpoint, status='500').inc()
                request_latency.labels(method=method, endpoint=endpoint).observe(time.time() - start)
                raise
        return wrapped
    return decorator


__all__ = [
    'metrics_bp',
    'metrics',
    'request_count',
    'request_latency',
    'active_users',
    'active_deals',
    'total_volume_usdt',
    'disputes_open',
    'payments_pending',
    'login_attempts',
    'registrations',
    'two_fa_enabled',
    'files_uploaded',
    'total_file_size',
    'track_request_metrics'
]

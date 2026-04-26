"""
Middleware层 - SafeSend API
طبقة الوسيط لـ SafeSend API

Applies security, logging, tracing, and rate limiting to all requests.
تطبق سياسات الأمان، التسجيل، التتبع، وتحديد المعدل على جميع الطلبات.
"""

import time
import uuid
from flask import Flask, g, request, jsonify, current_app
from typing import Optional, Any
import structlog

logger = structlog.get_logger(__name__)

def setup_middleware(app: Flask) -> None:
    """
    Register all middleware functions with the Flask application.
    تسجيل جميع دوال الوسيط مع تطبيق Flask.
    """
    app.before_request(before_request_handler)
    app.after_request(after_request_handler)
    app.teardown_request(teardown_request_handler)
    
    app.register_error_handler(429, rate_limit_exceeded_handler)
    
    logger.info("middleware.configured")

def before_request_handler() -> None:
    """
    Actions before each request processing.
    إجراءات ما قبل معالجة كل طلب.
    """
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    
    structlog.contextvars.bind_contextvars(
        request_id=g.request_id,
        method=request.method,
        path=request.path
    )
    
    logger.debug(
        "request.started",
        remote_addr=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

def after_request_handler(response) -> Any:
    """
    Actions after each request processing.
    إجراءات ما بعد معالجة كل طلب.
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['X-Request-ID'] = g.get('request_id', '')
    
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        response.headers['X-Response-Time'] = f"{duration:.4f}s"
        
        logger.debug(
            "request.completed",
            status_code=response.status_code,
            duration=f"{duration:.4f}s"
        )
    
    return response

def teardown_request_handler(error: Optional[Exception] = None) -> None:
    """
    Cleanup after each request regardless of success/failure.
    تنظيف الموارد بعد كل طلب بغض النظر عن النجاح أو الفشل.
    """
    if error:
        logger.error("request.error", error=str(error))
    
    structlog.contextvars.clear_contextvars()

def rate_limit_exceeded_handler(e) -> tuple:
    """
    Handler for rate limit exceeding (429 Too Many Requests).
    معالج تجاوز معدل الطلبات (429 طلبات كثيرة جداً).
    """
    logger.warning("rate_limit.exceeded", ip=request.remote_addr)
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.',
        'message_ar': 'تجاوزت الحد المسموح من الطلبات. حاول مرة أخرى لاحقاً.'
    }), 429

def rate_limit_by_user_middleware() -> Optional[tuple]:
    """
    Check rate limits based on user role.
    فحص حدود المعدل بناءً على دور المستخدم.
    
    يتم الاعتماد على Flask-Limiter في التنفيذ الفعلي عبر الـ decorators.
    هذه الدالة توفر نقطة تخصيص لمنطق إضافي مستقبلي.
    """
    limits = {
        'admin': 300,
        'user': 60,
        'anonymous': 10
    }
    
    user_role = getattr(g, 'user_role', 'anonymous')
    current_limit = limits.get(user_role, 10)
    
    logger.debug("rate_limit.check", role=user_role, limit=current_limit)
    return None

def cors_middleware() -> Optional[tuple]:
    """
    Validate CORS origin from allowed list.
    التحقق من مصدر CORS من القائمة المسموحة.
    """
    allowed_origins = current_app.config.get('CORS_ALLOWED_ORIGINS', [])
    origin = request.headers.get('Origin')
    
    if origin and '*' not in allowed_origins and origin not in allowed_origins:
        logger.warning("cors.blocked", origin=origin)
        return jsonify({'error': 'Origin not allowed', 'message_ar': 'المصدر غير مسموح به'}), 403
    
    return None

__all__ = [
    'setup_middleware',
    'before_request_handler',
    'after_request_handler',
    'teardown_request_handler',
    'rate_limit_exceeded_handler',
    'rate_limit_by_user_middleware',
    'cors_middleware'
]

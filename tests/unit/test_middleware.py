"""
اختبارات middleware.py
Unit Tests for middleware.py
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from flask import Flask, g

import sys
sys.path.insert(0, '.')

from src.api.middleware import (
    setup_middleware,
    before_request_handler,
    after_request_handler,
    teardown_request_handler,
    rate_limit_exceeded_handler,
    rate_limit_by_user_middleware,
    cors_middleware
)

@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['CORS_ALLOWED_ORIGINS'] = ['http://localhost:3000']
    return app

class TestSetupMiddleware:
    """Tests for setup_middleware function."""
    
    def test_setup_registers_handlers(self, app):
        """Verify that all handlers are registered."""
        setup_middleware(app)
        
        assert len(app.before_request_funcs) > 0
        assert len(app.after_request_funcs) > 0
        assert len(app.teardown_request_funcs) > 0

class TestBeforeRequest:
    """Tests for before_request_handler."""
    
    def test_sets_request_id(self, app):
        """Verify that request_id is set in g."""
        with app.test_request_context('/'):
            before_request_handler()
            assert hasattr(g, 'request_id')
            assert len(g.request_id) == 36  # UUID format
    
    def test_sets_start_time(self, app):
        """Verify that start_time is set in g."""
        with app.test_request_context('/'):
            before_request_handler()
            assert hasattr(g, 'start_time')
            assert isinstance(g.start_time, float)

class TestAfterRequest:
    """Tests for after_request_handler."""
    
    def test_adds_security_headers(self, app):
        """Verify that all security headers are added."""
        with app.test_request_context('/'):
            before_request_handler()
            response = app.make_response(('OK', 200))
            response = after_request_handler(response)
            
            assert response.headers['X-Content-Type-Options'] == 'nosniff'
            assert response.headers['X-Frame-Options'] == 'DENY'
            assert response.headers['Content-Security-Policy'] == "default-src 'self'"
    
    def test_adds_request_id_header(self, app):
        """Verify that X-Request-ID header is added."""
        with app.test_request_context('/'):
            before_request_handler()
            response = app.make_response(('OK', 200))
            response = after_request_handler(response)
            
            assert 'X-Request-ID' in response.headers
    
    def test_adds_response_time_header(self, app):
        """Verify that X-Response-Time header is added."""
        with app.test_request_context('/'):
            before_request_handler()
            response = app.make_response(('OK', 200))
            response = after_request_handler(response)
            
            assert 'X-Response-Time' in response.headers

class TestTeardownRequest:
    """Tests for teardown_request_handler."""
    
    def test_handles_error(self, app):
        """Verify that teardown doesn't raise on error."""
        with app.test_request_context('/'):
            # Should not raise
            teardown_request_handler(Exception("Test error"))
    
    def test_handles_normal_teardown(self, app):
        """Verify that teardown works without error."""
        with app.test_request_context('/'):
            # Should not raise
            teardown_request_handler(None)

class TestRateLimitExceeded:
    """Tests for rate_limit_exceeded_handler."""
    
    def test_returns_429_with_json(self, app):
        """Verify that 429 response contains proper JSON."""
        with app.test_request_context('/'):
            response = rate_limit_exceeded_handler(None)
            assert response[1] == 429
            assert 'error' in response[0].json

class TestRateLimitByUser:
    """Tests for rate_limit_by_user_middleware."""
    
    def test_anonymous_user_returns_none(self, app):
        """Verify that anonymous user check returns None."""
        with app.test_request_context('/'):
            result = rate_limit_by_user_middleware()
            assert result is None
    
    def test_admin_user_returns_none(self, app):
        """Verify that admin user check returns None."""
        with app.test_request_context('/'):
            g.user_role = 'admin'
            result = rate_limit_by_user_middleware()
            assert result is None

class TestCorsMiddleware:
    """Tests for cors_middleware."""
    
    def test_allowed_origin_returns_none(self, app):
        """Verify that allowed origin passes CORS check."""
        with app.test_request_context('/', headers={'Origin': 'http://localhost:3000'}):
            result = cors_middleware()
            assert result is None
    
    def test_blocked_origin_returns_403(self, app):
        """Verify that blocked origin gets 403."""
        with app.test_request_context('/', headers={'Origin': 'http://evil.com'}):
            result = cors_middleware()
            assert result is not None
            assert result[1] == 403

__all__ = [
    'TestSetupMiddleware',
    'TestBeforeRequest',
    'TestAfterRequest',
    'TestTeardownRequest',
    'TestRateLimitExceeded',
    'TestRateLimitByUser',
    'TestCorsMiddleware'
]

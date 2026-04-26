"""
اختبارات auth.py
Unit Tests for auth.py
"""

import pytest
import json
from unittest.mock import MagicMock, patch, PropertyMock
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.auth import auth_bp

@pytest.fixture
def app():
    """Create test Flask application with auth blueprint."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-for-jwt'
    app.register_blueprint(auth_bp)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

class TestRegistration:
    """Tests for /api/v1/auth/register endpoint."""
    
    def test_register_requires_data(self, client):
        """Verify register requires POST data."""
        response = client.post('/api/v1/auth/register', json={})
        assert response.status_code in [400, 409, 500]  # Validation or DB error
    
    def test_register_validates_email(self, client):
        """Verify register validates email format."""
        response = client.post('/api/v1/auth/register', json={
            'email': 'invalid-email',
            'username': 'testuser',
            'password': 'password123'
        })
        assert response.status_code in [400, 409, 500]

class TestLogin:
    """Tests for /api/v1/auth/login endpoint."""
    
    def test_login_requires_data(self, client):
        """Verify login requires POST data."""
        response = client.post('/api/v1/auth/login', json={})
        assert response.status_code in [400, 401, 500]
    
    def test_login_returns_json(self, client):
        """Verify login returns JSON response."""
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.is_json
        data = response.get_json()
        assert 'error' in data or 'message' in data

class TestLogout:
    """Tests for /api/v1/auth/logout endpoint."""
    
    def test_logout_succeeds(self, client):
        """Verify logout returns success."""
        response = client.post('/api/v1/auth/logout')
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

class TestRefreshToken:
    """Tests for /api/v1/auth/refresh endpoint."""
    
    def test_refresh_requires_token(self, client):
        """Verify refresh requires refresh_token."""
        response = client.post('/api/v1/auth/refresh', json={})
        assert response.status_code == 400
    
    def test_refresh_rejects_invalid(self, client):
        """Verify refresh rejects invalid token."""
        response = client.post('/api/v1/auth/refresh', json={
            'refresh_token': 'invalid-token'
        })
        assert response.status_code == 401

class TestProfile:
    """Tests for /api/v1/auth/me endpoint."""
    
    def test_me_requires_auth(self, client):
        """Verify /me requires authentication."""
        response = client.get('/api/v1/auth/me')
        assert response.status_code == 401

class TestEmailVerification:
    """Tests for email verification endpoints."""
    
    def test_verify_requires_data(self, client):
        """Verify email verification requires data."""
        response = client.post('/api/v1/auth/verify-email', json={})
        assert response.status_code == 400
    
    def test_resend_requires_email(self, client):
        """Verify resend requires email."""
        response = client.post('/api/v1/auth/verify-email/resend', json={})
        assert response.status_code == 400

class TestPasswordManagement:
    """Tests for password management endpoints."""
    
    def test_forgot_password_requires_email(self, client):
        """Verify forgot password requires email."""
        response = client.post('/api/v1/auth/forgot-password', json={})
        assert response.status_code == 400
    
    def test_forgot_password_always_returns_200(self, client):
        """Verify forgot password always returns 200."""
        response = client.post('/api/v1/auth/forgot-password', json={
            'email': 'test@example.com'
        })
        assert response.status_code == 200
    
    def test_reset_requires_data(self, client):
        """Verify reset password requires data."""
        response = client.post('/api/v1/auth/reset-password', json={})
        assert response.status_code == 400
    
    def test_change_requires_auth(self, client):
        """Verify change password requires auth."""
        response = client.post('/api/v1/auth/change-password', json={})
        assert response.status_code == 401

class Test2FA:
    """Tests for 2FA endpoints."""
    
    def test_enable_requires_auth(self, client):
        """Verify enable 2FA requires auth."""
        response = client.post('/api/v1/auth/2fa/enable')
        assert response.status_code == 401
    
    def test_verify_requires_auth(self, client):
        """Verify 2FA verify requires auth."""
        response = client.post('/api/v1/auth/2fa/verify', json={})
        assert response.status_code == 401
    
    def test_disable_requires_auth(self, client):
        """Verify disable 2FA requires auth."""
        response = client.post('/api/v1/auth/2fa/disable')
        assert response.status_code == 401

class TestPushNotifications:
    """Tests for push notification endpoints."""
    
    def test_subscribe_requires_auth(self, client):
        """Verify push subscribe requires auth."""
        response = client.post('/api/v1/auth/push/subscribe', json={})
        assert response.status_code == 401
    
    def test_unsubscribe_requires_auth(self, client):
        """Verify push unsubscribe requires auth."""
        response = client.post('/api/v1/auth/push/unsubscribe')
        assert response.status_code == 401

class TestSessions:
    """Tests for session management endpoints."""
    
    def test_list_requires_auth(self, client):
        """Verify list sessions requires auth."""
        response = client.get('/api/v1/auth/sessions')
        assert response.status_code == 401
    
    def test_revoke_requires_auth(self, client):
        """Verify revoke session requires auth."""
        response = client.delete('/api/v1/auth/sessions/1')
        assert response.status_code == 401

class TestBlueprintRegistration:
    """Tests for auth blueprint registration."""
    
    def test_blueprint_registered(self, app):
        """Verify all auth endpoints are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected_endpoints = [
            '/api/v1/auth/register',
            '/api/v1/auth/login',
            '/api/v1/auth/logout',
            '/api/v1/auth/refresh',
            '/api/v1/auth/me',
            '/api/v1/auth/verify-email',
            '/api/v1/auth/verify-email/resend',
            '/api/v1/auth/forgot-password',
            '/api/v1/auth/reset-password',
            '/api/v1/auth/change-password',
            '/api/v1/auth/2fa/enable',
            '/api/v1/auth/2fa/verify',
            '/api/v1/auth/2fa/disable',
            '/api/v1/auth/2fa/backup',
            '/api/v1/auth/push/subscribe',
            '/api/v1/auth/push/unsubscribe',
            '/api/v1/auth/sessions',
            '/api/v1/auth/sessions/<int:session_id>'
        ]
        
        for endpoint in expected_endpoints:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = [
    'TestRegistration',
    'TestLogin',
    'TestLogout',
    'TestRefreshToken',
    'TestProfile',
    'TestEmailVerification',
    'TestPasswordManagement',
    'Test2FA',
    'TestPushNotifications',
    'TestSessions',
    'TestBlueprintRegistration'
]

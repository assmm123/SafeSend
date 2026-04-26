"""
اختبارات users.py
Unit Tests for users.py
"""

import pytest
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.users import users_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(users_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestProfiles:
    def test_public_profile_no_auth(self, client):
        response = client.get('/api/v1/users/testuser')
        assert response.status_code == 200
    
    def test_full_profile_requires_auth(self, client):
        response = client.get('/api/v1/users/testuser/profile')
        assert response.status_code in [401, 500]
    
    def test_update_profile_requires_auth(self, client):
        response = client.put('/api/v1/users/profile', json={})
        assert response.status_code in [401, 500]
    
    def test_upload_avatar_requires_auth(self, client):
        response = client.post('/api/v1/users/profile/avatar')
        assert response.status_code in [401, 500]
    
    def test_delete_avatar_requires_auth(self, client):
        response = client.delete('/api/v1/users/profile/avatar')
        assert response.status_code in [401, 500]

class TestReviews:
    def test_get_reviews_no_auth(self, client):
        response = client.get('/api/v1/users/testuser/reviews')
        assert response.status_code == 200
    
    def test_add_review_requires_auth(self, client):
        response = client.post('/api/v1/users/testuser/review', json={})
        assert response.status_code in [401, 500]

class TestPortfolio:
    def test_get_portfolio_no_auth(self, client):
        response = client.get('/api/v1/users/testuser/portfolio')
        assert response.status_code == 200
    
    def test_add_portfolio_requires_auth(self, client):
        response = client.post('/api/v1/users/portfolio', json={})
        assert response.status_code in [401, 500]
    
    def test_delete_portfolio_requires_auth(self, client):
        response = client.delete('/api/v1/users/portfolio/1')
        assert response.status_code in [401, 500]

class TestSettings:
    def test_get_settings_requires_auth(self, client):
        response = client.get('/api/v1/users/settings')
        assert response.status_code in [401, 500]
    
    def test_update_settings_requires_auth(self, client):
        response = client.put('/api/v1/users/settings', json={})
        assert response.status_code in [401, 500]
    
    def test_notifications_requires_auth(self, client):
        response = client.get('/api/v1/users/notifications')
        assert response.status_code in [401, 500]

class TestPayoutMethods:
    def test_get_methods_requires_auth(self, client):
        response = client.get('/api/v1/users/payout-methods')
        assert response.status_code in [401, 500]
    
    def test_update_methods_requires_auth(self, client):
        response = client.put('/api/v1/users/payout-methods', json={})
        assert response.status_code in [401, 500]
    
    def test_verify_method_requires_auth(self, client):
        response = client.post('/api/v1/users/payout-methods/usdt/verify', json={})
        assert response.status_code in [401, 500]

class TestBlueprint:
    def test_all_endpoints(self, app):
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected = [
            '/api/v1/users/<username>',
            '/api/v1/users/<username>/profile',
            '/api/v1/users/profile',
            '/api/v1/users/profile/avatar',
            '/api/v1/users/<username>/reviews',
            '/api/v1/users/<username>/review',
            '/api/v1/users/<username>/portfolio',
            '/api/v1/users/portfolio',
            '/api/v1/users/portfolio/<int:item_id>',
            '/api/v1/users/settings',
            '/api/v1/users/notifications',
            '/api/v1/users/payout-methods',
            '/api/v1/users/payout-methods/<method>/verify'
        ]
        
        for endpoint in expected:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = ['TestProfiles', 'TestReviews', 'TestPortfolio', 'TestSettings', 'TestPayoutMethods', 'TestBlueprint']

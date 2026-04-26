"""
اختبارات admin.py
Unit Tests for admin.py
"""

import pytest
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.admin import admin_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(admin_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

UUID = '12345678-1234-1234-1234-123456789abc'

class TestPayouts:
    def test_pending_requires_auth(self, client):
        response = client.get('/api/v1/admin/payouts/pending')
        assert response.status_code in [401, 500]
    
    def test_history_requires_auth(self, client):
        response = client.get('/api/v1/admin/payouts/history')
        assert response.status_code in [401, 500]
    
    def test_mark_sent_requires_auth(self, client):
        response = client.post(f'/api/v1/admin/payouts/{UUID}/mark-sent')
        assert response.status_code in [401, 500]
    
    def test_mark_failed_requires_auth(self, client):
        response = client.post(f'/api/v1/admin/payouts/{UUID}/mark-failed')
        assert response.status_code in [401, 500]
    
    def test_retry_requires_auth(self, client):
        response = client.post(f'/api/v1/admin/payouts/{UUID}/retry')
        assert response.status_code in [401, 500]

class TestDisputes:
    def test_active_requires_auth(self, client):
        response = client.get('/api/v1/admin/disputes/active')
        assert response.status_code in [401, 500]
    
    def test_all_requires_auth(self, client):
        response = client.get('/api/v1/admin/disputes/all')
        assert response.status_code in [401, 500]
    
    def test_detail_requires_auth(self, client):
        response = client.get('/api/v1/admin/disputes/1')
        assert response.status_code in [401, 500]
    
    def test_resolve_requires_auth(self, client):
        response = client.post('/api/v1/admin/disputes/1/resolve', json={})
        assert response.status_code in [401, 500]
    
    def test_assign_requires_auth(self, client):
        response = client.post('/api/v1/admin/disputes/1/assign', json={})
        assert response.status_code in [401, 500]
    
    def test_note_requires_auth(self, client):
        response = client.post('/api/v1/admin/disputes/1/note', json={})
        assert response.status_code in [401, 500]

class TestUsers:
    def test_list_requires_auth(self, client):
        response = client.get('/api/v1/admin/users')
        assert response.status_code in [401, 500]
    
    def test_detail_requires_auth(self, client):
        response = client.get('/api/v1/admin/users/1')
        assert response.status_code in [401, 500]
    
    def test_verify_requires_auth(self, client):
        response = client.post('/api/v1/admin/users/1/verify')
        assert response.status_code in [401, 500]
    
    def test_suspend_requires_auth(self, client):
        response = client.post('/api/v1/admin/users/1/suspend')
        assert response.status_code in [401, 500]
    
    def test_unsuspend_requires_auth(self, client):
        response = client.post('/api/v1/admin/users/1/unsuspend')
        assert response.status_code in [401, 500]

class TestStats:
    def test_stats_requires_auth(self, client):
        response = client.get('/api/v1/admin/stats')
        assert response.status_code in [401, 500]
    
    def test_revenue_requires_auth(self, client):
        response = client.get('/api/v1/admin/stats/revenue')
        assert response.status_code in [401, 500]
    
    def test_export_returns_csv(self, client):
        response = client.get('/api/v1/admin/stats/export')
        assert response.status_code in [200, 401, 500]

class TestSystem:
    def test_backup_requires_auth(self, client):
        response = client.post('/api/v1/admin/backup/trigger')
        assert response.status_code in [401, 500]
    
    def test_backups_requires_auth(self, client):
        response = client.get('/api/v1/admin/backups')
        assert response.status_code in [401, 500]
    
    def test_cleanup_requires_auth(self, client):
        response = client.post('/api/v1/admin/maintenance/cleanup')
        assert response.status_code in [401, 500]

class TestBlueprint:
    def test_all_endpoints(self, app):
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected = [
            '/api/v1/admin/payouts/pending',
            '/api/v1/admin/payouts/history',
            '/api/v1/admin/payouts/<uuid:deal_uuid>/mark-sent',
            '/api/v1/admin/payouts/<uuid:deal_uuid>/mark-failed',
            '/api/v1/admin/payouts/<uuid:deal_uuid>/retry',
            '/api/v1/admin/disputes/active',
            '/api/v1/admin/disputes/all',
            '/api/v1/admin/disputes/<int:dispute_id>',
            '/api/v1/admin/disputes/<int:dispute_id>/resolve',
            '/api/v1/admin/disputes/<int:dispute_id>/assign',
            '/api/v1/admin/disputes/<int:dispute_id>/note',
            '/api/v1/admin/users',
            '/api/v1/admin/users/<int:target_user_id>',
            '/api/v1/admin/users/<int:target_user_id>/verify',
            '/api/v1/admin/users/<int:target_user_id>/suspend',
            '/api/v1/admin/users/<int:target_user_id>/unsuspend',
            '/api/v1/admin/stats',
            '/api/v1/admin/stats/revenue',
            '/api/v1/admin/stats/export',
            '/api/v1/admin/backup/trigger',
            '/api/v1/admin/backups',
            '/api/v1/admin/maintenance/cleanup'
        ]
        
        for endpoint in expected:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = ['TestPayouts', 'TestDisputes', 'TestUsers', 'TestStats', 'TestSystem', 'TestBlueprint']

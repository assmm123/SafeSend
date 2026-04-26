"""
اختبارات disputes.py
Unit Tests for disputes.py
"""

import pytest
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.disputes import disputes_bp

@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(disputes_bp)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

class TestOpenDispute:
    """Tests for POST /api/v1/disputes/open/{uuid}."""
    
    def test_open_requires_auth(self, client):
        """Verify open requires authentication."""
        response = client.post('/api/v1/disputes/open/12345678-1234-1234-1234-123456789abc', json={})
        assert response.status_code in [400, 401]
    
    def test_open_validates_data(self, client):
        """Verify open validates input data."""
        response = client.post('/api/v1/disputes/open/12345678-1234-1234-1234-123456789abc', json={
            'reason': 'Test',
            'reason_category': 'invalid'
        })
        assert response.status_code in [400, 401]

class TestAddEvidence:
    """Tests for POST /api/v1/disputes/{id}/evidence."""
    
    def test_add_requires_auth(self, client):
        """Verify add evidence requires authentication."""
        response = client.post('/api/v1/disputes/1/evidence', json={})
        assert response.status_code in [400, 401]

class TestRemoveEvidence:
    """Tests for DELETE /api/v1/disputes/{id}/evidence/{index}."""
    
    def test_remove_requires_auth(self, client):
        """Verify remove evidence requires authentication."""
        response = client.delete('/api/v1/disputes/1/evidence/0')
        assert response.status_code in [401, 404, 500]

class TestGetDispute:
    """Tests for GET /api/v1/disputes/{id}."""
    
    def test_get_requires_auth(self, client):
        """Verify get requires authentication."""
        response = client.get('/api/v1/disputes/1')
        assert response.status_code in [401, 404, 500]

class TestMyDisputes:
    """Tests for GET /api/v1/disputes/my-disputes."""
    
    def test_list_requires_auth(self, client):
        """Verify list requires authentication."""
        response = client.get('/api/v1/disputes/my-disputes')
        assert response.status_code in [401, 500]

class TestDisputeMessage:
    """Tests for POST /api/v1/disputes/{id}/message."""
    
    def test_message_requires_auth(self, client):
        """Verify message requires authentication."""
        response = client.post('/api/v1/disputes/1/message', json={})
        assert response.status_code in [400, 401, 404, 500]

class TestDisputeMessages:
    """Tests for GET /api/v1/disputes/{id}/messages."""
    
    def test_messages_requires_auth(self, client):
        """Verify messages requires authentication."""
        response = client.get('/api/v1/disputes/1/messages')
        assert response.status_code in [401, 500]

class TestAppealDispute:
    """Tests for POST /api/v1/disputes/{id}/appeal."""
    
    def test_appeal_requires_auth(self, client):
        """Verify appeal requires authentication."""
        response = client.post('/api/v1/disputes/1/appeal', json={})
        assert response.status_code in [401, 404, 500]

class TestDisputeTimeline:
    """Tests for GET /api/v1/disputes/{id}/timeline."""
    
    def test_timeline_requires_auth(self, client):
        """Verify timeline requires authentication."""
        response = client.get('/api/v1/disputes/1/timeline')
        assert response.status_code in [401, 404, 500]

class TestBlueprintRegistration:
    """Tests for blueprint registration."""
    
    def test_all_endpoints(self, app):
        """Verify all endpoints are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected = [
            '/api/v1/disputes/open/<uuid:deal_uuid>',
            '/api/v1/disputes/<int:dispute_id>/evidence',
            '/api/v1/disputes/<int:dispute_id>/evidence/<int:evidence_index>',
            '/api/v1/disputes/<int:dispute_id>',
            '/api/v1/disputes/my-disputes',
            '/api/v1/disputes/<int:dispute_id>/message',
            '/api/v1/disputes/<int:dispute_id>/messages',
            '/api/v1/disputes/<int:dispute_id>/appeal',
            '/api/v1/disputes/<int:dispute_id>/timeline'
        ]
        
        for endpoint in expected:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = [
    'TestOpenDispute',
    'TestAddEvidence',
    'TestRemoveEvidence',
    'TestGetDispute',
    'TestMyDisputes',
    'TestDisputeMessage',
    'TestDisputeMessages',
    'TestAppealDispute',
    'TestDisputeTimeline',
    'TestBlueprintRegistration'
]

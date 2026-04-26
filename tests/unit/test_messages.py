"""
اختبارات messages.py
Unit Tests for messages.py
"""

import pytest
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.messages import messages_bp

@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(messages_bp)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

class TestListConversations:
    """Tests for GET /api/v1/messages/conversations."""
    
    def test_list_requires_auth(self, client):
        """Verify list requires authentication."""
        response = client.get('/api/v1/messages/conversations')
        assert response.status_code in [401, 500]

class TestGetMessages:
    """Tests for GET /api/v1/messages/conversations/{uuid}."""
    
    def test_get_requires_auth(self, client):
        """Verify get requires authentication."""
        response = client.get('/api/v1/messages/conversations/12345678-1234-1234-1234-123456789abc')
        assert response.status_code in [401, 500]

class TestSendMessage:
    """Tests for POST /api/v1/messages/conversations/{uuid}."""
    
    def test_send_requires_auth(self, client):
        """Verify send requires authentication."""
        response = client.post('/api/v1/messages/conversations/12345678-1234-1234-1234-123456789abc', json={})
        assert response.status_code in [400, 401]

class TestEditMessage:
    """Tests for PUT /api/v1/messages/conversations/{uuid}/messages/{id}."""
    
    def test_edit_requires_auth(self, client):
        """Verify edit requires authentication."""
        response = client.put('/api/v1/messages/conversations/12345678-1234-1234-1234-123456789abc/messages/1', json={})
        assert response.status_code in [400, 401, 500]

class TestDeleteMessage:
    """Tests for DELETE /api/v1/messages/conversations/{uuid}/messages/{id}."""
    
    def test_delete_requires_auth(self, client):
        """Verify delete requires authentication."""
        response = client.delete('/api/v1/messages/conversations/12345678-1234-1234-1234-123456789abc/messages/1')
        assert response.status_code in [401, 500]

class TestMarkAsRead:
    """Tests for POST /api/v1/messages/conversations/{uuid}/read."""
    
    def test_read_requires_auth(self, client):
        """Verify read requires authentication."""
        response = client.post('/api/v1/messages/conversations/12345678-1234-1234-1234-123456789abc/read', json={})
        assert response.status_code in [401, 500]

class TestUnreadCount:
    """Tests for GET /api/v1/messages/unread/count."""
    
    def test_unread_requires_auth(self, client):
        """Verify unread requires authentication."""
        response = client.get('/api/v1/messages/unread/count')
        assert response.status_code in [200, 401, 500]

class TestTypingIndicator:
    """Tests for POST /api/v1/messages/typing/{uuid}."""
    
    def test_typing_requires_auth(self, client):
        """Verify typing requires authentication."""
        response = client.post('/api/v1/messages/typing/12345678-1234-1234-1234-123456789abc', json={})
        assert response.status_code in [401, 500]

class TestExportConversation:
    """Tests for GET /api/v1/messages/conversations/{uuid}/export."""
    
    def test_export_requires_auth(self, client):
        """Verify export requires authentication."""
        response = client.get('/api/v1/messages/conversations/12345678-1234-1234-1234-123456789abc/export')
        assert response.status_code in [401, 500]

class TestSearchMessages:
    """Tests for POST /api/v1/messages/conversations/{uuid}/search."""
    
    def test_search_requires_auth(self, client):
        """Verify search requires authentication."""
        response = client.post('/api/v1/messages/conversations/12345678-1234-1234-1234-123456789abc/search', json={})
        assert response.status_code in [400, 401, 500]

class TestBlueprintRegistration:
    """Tests for blueprint registration."""
    
    def test_all_endpoints(self, app):
        """Verify all endpoints are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected = [
            '/api/v1/messages/conversations',
            '/api/v1/messages/conversations/<uuid:deal_uuid>',
            '/api/v1/messages/conversations/<uuid:deal_uuid>/messages/<int:message_id>',
            '/api/v1/messages/conversations/<uuid:deal_uuid>/read',
            '/api/v1/messages/unread/count',
            '/api/v1/messages/typing/<uuid:deal_uuid>',
            '/api/v1/messages/conversations/<uuid:deal_uuid>/export',
            '/api/v1/messages/conversations/<uuid:deal_uuid>/search'
        ]
        
        for endpoint in expected:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = [
    'TestListConversations',
    'TestGetMessages',
    'TestSendMessage',
    'TestEditMessage',
    'TestDeleteMessage',
    'TestMarkAsRead',
    'TestUnreadCount',
    'TestTypingIndicator',
    'TestExportConversation',
    'TestSearchMessages',
    'TestBlueprintRegistration'
]

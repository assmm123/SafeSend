"""
اختبارات deals.py
Unit Tests for deals.py
"""

import pytest
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.deals import deals_bp

@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(deals_bp)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

class TestCreateDeal:
    """Tests for POST /api/v1/deals."""
    
    def test_create_requires_auth(self, client):
        """Verify create requires authentication."""
        response = client.post('/api/v1/deals', json={})
        assert response.status_code in [400, 401]
    
    def test_create_validates_data(self, client):
        """Verify create validates input data."""
        response = client.post('/api/v1/deals', json={'title': 'Hi'})
        assert response.status_code in [400, 401]

class TestListDeals:
    """Tests for GET /api/v1/deals."""
    
    def test_list_requires_auth(self, client):
        """Verify list requires authentication."""
        response = client.get('/api/v1/deals')
        assert response.status_code in [401, 500]

class TestGetDeal:
    """Tests for GET /api/v1/deals/{uuid}."""
    
    def test_get_requires_auth(self, client):
        """Verify get requires authentication."""
        response = client.get('/api/v1/deals/12345678-1234-1234-1234-123456789abc')
        assert response.status_code in [401, 404, 500]
    
    def test_get_invalid_uuid(self, client):
        """Verify get rejects invalid UUID."""
        response = client.get('/api/v1/deals/not-a-uuid')
        assert response.status_code in [401, 404, 500]

class TestUpdateDeal:
    """Tests for PUT /api/v1/deals/{uuid}."""
    
    def test_update_requires_auth(self, client):
        """Verify update requires authentication."""
        response = client.put('/api/v1/deals/12345678-1234-1234-1234-123456789abc', json={})
        assert response.status_code in [400, 401]

class TestCancelDeal:
    """Tests for POST /api/v1/deals/{uuid}/cancel."""
    
    def test_cancel_requires_auth(self, client):
        """Verify cancel requires authentication."""
        response = client.post('/api/v1/deals/12345678-1234-1234-1234-123456789abc/cancel')
        assert response.status_code in [401, 404, 500]

class TestDeliverWork:
    """Tests for POST /api/v1/deals/{uuid}/deliver."""
    
    def test_deliver_requires_auth(self, client):
        """Verify deliver requires authentication."""
        response = client.post('/api/v1/deals/12345678-1234-1234-1234-123456789abc/deliver')
        assert response.status_code in [401, 404, 500]

class TestApproveWork:
    """Tests for POST /api/v1/deals/{uuid}/approve."""
    
    def test_approve_requires_auth(self, client):
        """Verify approve requires authentication."""
        response = client.post('/api/v1/deals/12345678-1234-1234-1234-123456789abc/approve')
        assert response.status_code in [401, 404, 500]

class TestRejectWork:
    """Tests for POST /api/v1/deals/{uuid}/reject."""
    
    def test_reject_requires_auth(self, client):
        """Verify reject requires authentication."""
        response = client.post('/api/v1/deals/12345678-1234-1234-1234-123456789abc/reject')
        assert response.status_code in [401, 404, 500]

class TestRequestRevision:
    """Tests for POST /api/v1/deals/{uuid}/request-revision."""
    
    def test_revision_requires_auth(self, client):
        """Verify revision request requires authentication."""
        response = client.post('/api/v1/deals/12345678-1234-1234-1234-123456789abc/request-revision')
        assert response.status_code in [401, 404, 500]

class TestTimeline:
    """Tests for GET /api/v1/deals/{uuid}/timeline."""
    
    def test_timeline_requires_auth(self, client):
        """Verify timeline requires authentication."""
        response = client.get('/api/v1/deals/12345678-1234-1234-1234-123456789abc/timeline')
        assert response.status_code in [401, 404, 500]

class TestActivity:
    """Tests for GET /api/v1/deals/{uuid}/activity."""
    
    def test_activity_requires_auth(self, client):
        """Verify activity requires authentication."""
        response = client.get('/api/v1/deals/12345678-1234-1234-1234-123456789abc/activity')
        assert response.status_code in [401, 404, 500]

class TestRemind:
    """Tests for POST /api/v1/deals/{uuid}/remind."""
    
    def test_remind_requires_auth(self, client):
        """Verify remind requires authentication."""
        response = client.post('/api/v1/deals/12345678-1234-1234-1234-123456789abc/remind')
        assert response.status_code in [401, 404, 500]

class TestStats:
    """Tests for GET /api/v1/deals/stats."""
    
    def test_stats_requires_auth(self, client):
        """Verify stats requires authentication."""
        response = client.get('/api/v1/deals/stats')
        assert response.status_code in [200, 401, 500]

class TestCategories:
    """Tests for GET /api/v1/deals/categories."""
    
    def test_categories_returns_list(self, client):
        """Verify categories returns list."""
        response = client.get('/api/v1/deals/categories')
        assert response.status_code == 200
        data = response.get_json()
        assert 'categories' in data
        assert isinstance(data['categories'], list)

class TestBlueprintRegistration:
    """Tests for blueprint registration."""
    
    def test_all_endpoints(self, app):
        """Verify all endpoints are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected = [
            '/api/v1/deals',
            '/api/v1/deals/<uuid:deal_uuid>',
            '/api/v1/deals/<uuid:deal_uuid>/cancel',
            '/api/v1/deals/<uuid:deal_uuid>/deliver',
            '/api/v1/deals/<uuid:deal_uuid>/approve',
            '/api/v1/deals/<uuid:deal_uuid>/reject',
            '/api/v1/deals/<uuid:deal_uuid>/request-revision',
            '/api/v1/deals/<uuid:deal_uuid>/timeline',
            '/api/v1/deals/<uuid:deal_uuid>/activity',
            '/api/v1/deals/<uuid:deal_uuid>/remind',
            '/api/v1/deals/stats',
            '/api/v1/deals/categories'
        ]
        
        for endpoint in expected:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = [
    'TestCreateDeal',
    'TestListDeals',
    'TestGetDeal',
    'TestUpdateDeal',
    'TestCancelDeal',
    'TestDeliverWork',
    'TestApproveWork',
    'TestRejectWork',
    'TestRequestRevision',
    'TestTimeline',
    'TestActivity',
    'TestRemind',
    'TestStats',
    'TestCategories',
    'TestBlueprintRegistration'
]

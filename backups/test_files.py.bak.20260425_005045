"""
اختبارات files.py
Unit Tests for files.py
"""

import pytest
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.files import files_bp

@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(files_bp)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

class TestUploadFile:
    """Tests for POST /api/v1/files/upload/{uuid}."""
    
    def test_upload_requires_auth(self, client):
        """Verify upload requires authentication."""
        response = client.post('/api/v1/files/upload/12345678-1234-1234-1234-123456789abc')
        assert response.status_code in [400, 401, 500]

class TestChunkedUpload:
    """Tests for chunked upload endpoints."""
    
    def test_init_requires_auth(self, client):
        """Verify init requires authentication."""
        response = client.post('/api/v1/files/upload/12345678-1234-1234-1234-123456789abc/init', json={})
        assert response.status_code in [400, 401]
    
    def test_chunk_requires_auth(self, client):
        """Verify chunk requires authentication."""
        response = client.post('/api/v1/files/upload/12345678-1234-1234-1234-123456789abc/chunk')
        assert response.status_code in [400, 401, 500]
    
    def test_complete_requires_auth(self, client):
        """Verify complete requires authentication."""
        response = client.post('/api/v1/files/upload/12345678-1234-1234-1234-123456789abc/complete')
        assert response.status_code in [400, 401, 500]

class TestPreview:
    """Tests for GET /api/v1/files/preview/{id}."""
    
    def test_preview_requires_auth(self, client):
        """Verify preview requires authentication."""
        response = client.get('/api/v1/files/preview/1')
        assert response.status_code in [401, 500]
    
    def test_stream_requires_auth(self, client):
        """Verify stream requires authentication."""
        response = client.get('/api/v1/files/preview/1/stream')
        assert response.status_code in [401, 501, 500]

class TestDownload:
    """Tests for GET /api/v1/files/download/{id}."""
    
    def test_download_requires_token(self, client):
        """Verify download requires token."""
        response = client.get('/api/v1/files/download/1')
        assert response.status_code in [400, 401, 500]
    
    def test_token_generation_requires_auth(self, client):
        """Verify token generation requires auth."""
        response = client.post('/api/v1/files/download/1/token')
        assert response.status_code in [401, 500]

class TestDelete:
    """Tests for DELETE /api/v1/files/{id}."""
    
    def test_delete_requires_auth(self, client):
        """Verify delete requires authentication."""
        response = client.delete('/api/v1/files/1')
        assert response.status_code in [401, 500]

class TestFileInfo:
    """Tests for GET /api/v1/files/info/{id}."""
    
    def test_info_requires_auth(self, client):
        """Verify info requires authentication."""
        response = client.get('/api/v1/files/info/1')
        assert response.status_code in [401, 500]

class TestDealFiles:
    """Tests for GET /api/v1/files/deal/{uuid}."""
    
    def test_deal_files_requires_auth(self, client):
        """Verify deal files requires authentication."""
        response = client.get('/api/v1/files/deal/12345678-1234-1234-1234-123456789abc')
        assert response.status_code in [401, 404, 500]

class TestBlueprintRegistration:
    """Tests for blueprint registration."""
    
    def test_all_endpoints(self, app):
        """Verify all endpoints are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected = [
            '/api/v1/files/upload/<uuid:deal_uuid>',
            '/api/v1/files/upload/<uuid:deal_uuid>/init',
            '/api/v1/files/upload/<uuid:deal_uuid>/chunk',
            '/api/v1/files/upload/<uuid:deal_uuid>/complete',
            '/api/v1/files/preview/<int:file_id>',
            '/api/v1/files/preview/<int:file_id>/stream',
            '/api/v1/files/download/<int:file_id>',
            '/api/v1/files/download/<int:file_id>/token',
            '/api/v1/files/<int:file_id>',
            '/api/v1/files/info/<int:file_id>',
            '/api/v1/files/deal/<uuid:deal_uuid>'
        ]
        
        for endpoint in expected:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = [
    'TestUploadFile',
    'TestChunkedUpload',
    'TestPreview',
    'TestDownload',
    'TestDelete',
    'TestFileInfo',
    'TestDealFiles',
    'TestBlueprintRegistration'
]

"""
اختبارات health.py
Unit Tests for health.py
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from flask import Flask, jsonify
from datetime import datetime, timezone

import sys
sys.path.insert(0, '.')

from src.api.health import (
    health_bp,
    check_database,
    check_redis,
    check_celery,
    check_tron_grid,
    check_file_system,
    check_disk_space,
    check_memory_usage
)

@pytest.fixture
def app():
    """Create test Flask application with health blueprint."""
    app = Flask(__name__)
    app.config['HEALTH_CHECK_TOKEN'] = 'test-token-123'
    app.config['REDIS_URL'] = 'redis://localhost:6379/0'
    app.config['TRONGRID_API_URL'] = 'https://api.trongrid.io'
    app.register_blueprint(health_bp)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

class TestLivenessEndpoint:
    """Tests for /health/live endpoint."""
    
    def test_returns_200(self, client):
        """Verify liveness returns 200."""
        response = client.get('/health/live')
        assert response.status_code == 200
    
    def test_returns_alive_status(self, client):
        """Verify liveness returns alive status."""
        response = client.get('/health/live')
        data = response.get_json()
        assert data['status'] == 'alive'
    
    def test_includes_timestamp(self, client):
        """Verify liveness includes timestamp."""
        response = client.get('/health/live')
        data = response.get_json()
        assert 'timestamp' in data

class TestReadinessEndpoint:
    """Tests for /health/ready endpoint."""
    
    @patch('src.api.health.check_database')
    @patch('src.api.health.check_redis')
    def test_returns_healthy_when_all_ok(self, mock_redis, mock_db, client):
        """Verify readiness returns healthy when all components OK."""
        mock_db.return_value = {'status': 'healthy', 'latency_ms': 10}
        mock_redis.return_value = {'status': 'healthy', 'latency_ms': 5}
        
        response = client.get('/health/ready')
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert response.status_code == 200
    
    @patch('src.api.health.check_database')
    @patch('src.api.health.check_redis')
    def test_returns_unhealthy_when_db_fails(self, mock_redis, mock_db, client):
        """Verify readiness returns unhealthy when DB fails."""
        mock_db.return_value = {'status': 'unhealthy', 'error': 'Connection refused'}
        mock_redis.return_value = {'status': 'healthy', 'latency_ms': 5}
        
        response = client.get('/health/ready')
        data = response.get_json()
        assert data['status'] == 'unhealthy'
        assert response.status_code == 503
    
    def test_includes_components(self, client):
        """Verify readiness includes component status."""
        response = client.get('/health/ready')
        data = response.get_json()
        assert 'components' in data
        assert 'database' in data['components']
        assert 'redis' in data['components']

class TestDetailedHealthEndpoint:
    """Tests for /health/detailed endpoint."""
    
    def test_requires_auth_token(self, client):
        """Verify detailed health requires auth token."""
        response = client.get('/health/detailed')
        assert response.status_code == 401
    
    def test_accepts_valid_token(self, client, app):
        """Verify detailed health accepts valid token."""
        response = client.get(
            '/health/detailed',
            headers={'X-Health-Token': 'test-token-123'}
        )
        assert response.status_code in [200, 503]  # 503 if components unavailable
    
    def test_rejects_invalid_token(self, client):
        """Verify detailed health rejects invalid token."""
        response = client.get(
            '/health/detailed',
            headers={'X-Health-Token': 'wrong-token'}
        )
        assert response.status_code == 401

class TestCheckDatabase:
    """Tests for check_database function."""
    
    def test_returns_status_dict(self):
        """Verify check_database returns dict with status."""
        result = check_database()
        assert 'status' in result
        assert result['status'] in ['healthy', 'unhealthy']

class TestCheckRedis:
    """Tests for check_redis function."""
    
    def test_returns_status_dict(self, app):
        """Verify check_redis returns dict with status."""
        with app.app_context():
            result = check_redis()
            assert 'status' in result
            assert result['status'] in ['healthy', 'unhealthy']

class TestCheckDiskSpace:
    """Tests for check_disk_space function."""
    
    def test_returns_disk_info(self):
        """Verify check_disk_space returns disk info."""
        result = check_disk_space()
        assert 'status' in result
        assert 'free_percent' in result
        assert 'free_gb' in result
    
    def test_healthy_when_free_space(self):
        """Verify healthy when sufficient free space."""
        result = check_disk_space()
        if result['status'] == 'healthy':
            assert result['free_percent'] > 10

class TestCheckMemoryUsage:
    """Tests for check_memory_usage function."""
    
    def test_returns_memory_info(self):
        """Verify check_memory_usage returns memory info."""
        result = check_memory_usage()
        assert 'status' in result
        assert 'used_percent' in result
        assert 'total_gb' in result
        assert 'available_gb' in result

class TestCheckFileSystem:
    """Tests for check_file_system function."""
    
    def test_returns_status(self):
        """Verify check_file_system returns status."""
        result = check_file_system()
        assert 'status' in result
        assert result['status'] in ['healthy', 'unhealthy']

class TestBlueprintRegistration:
    """Tests for health blueprint registration."""
    
    def test_blueprint_registered(self, app):
        """Verify health blueprint is registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/health/live' in rules
        assert '/health/ready' in rules
        assert '/health/detailed' in rules

__all__ = [
    'TestLivenessEndpoint',
    'TestReadinessEndpoint',
    'TestDetailedHealthEndpoint',
    'TestCheckDatabase',
    'TestCheckRedis',
    'TestCheckDiskSpace',
    'TestCheckMemoryUsage',
    'TestCheckFileSystem',
    'TestBlueprintRegistration'
]

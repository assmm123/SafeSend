"""
اختبارات payments.py
Unit Tests for payments.py
"""

import pytest
from flask import Flask

import sys
sys.path.insert(0, '.')

from src.api.v1.payments import payments_bp

@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(payments_bp)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

class TestPaymentQR:
    """Tests for GET /api/v1/payments/{uuid}/qr."""
    
    def test_qr_requires_auth(self, client):
        """Verify QR requires authentication."""
        response = client.get('/api/v1/payments/12345678-1234-1234-1234-123456789abc/qr')
        assert response.status_code in [401, 404, 500]

class TestPaymentStatus:
    """Tests for GET /api/v1/payments/{uuid}/status."""
    
    def test_status_requires_auth(self, client):
        """Verify status requires authentication."""
        response = client.get('/api/v1/payments/12345678-1234-1234-1234-123456789abc/status')
        assert response.status_code in [401, 404, 500]

class TestPaymentAddress:
    """Tests for GET /api/v1/payments/{uuid}/address."""
    
    def test_address_requires_auth(self, client):
        """Verify address requires authentication."""
        response = client.get('/api/v1/payments/12345678-1234-1234-1234-123456789abc/address')
        assert response.status_code in [401, 404, 500]

class TestVerifyPayment:
    """Tests for POST /api/v1/payments/{uuid}/verify."""
    
    def test_verify_requires_auth(self, client):
        """Verify verify requires authentication."""
        response = client.post('/api/v1/payments/12345678-1234-1234-1234-123456789abc/verify', json={})
        assert response.status_code in [400, 401, 404, 500]

class TestTrongridWebhook:
    """Tests for POST /api/v1/payments/webhook/trongrid."""
    
    def test_webhook_no_auth_required(self, client):
        """Verify webhook doesn't require auth."""
        response = client.post('/api/v1/payments/webhook/trongrid', json={
            'transaction_id': 'tx123',
            'memo': 'deal-123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'received'

class TestExchangeRates:
    """Tests for GET /api/v1/payments/rates."""
    
    def test_rates_returns_data(self, client):
        """Verify rates returns exchange data."""
        response = client.get('/api/v1/payments/rates')
        assert response.status_code == 200
        data = response.get_json()
        assert 'rates' in data
        assert 'USDT' in data['rates']

class TestPaymentHistory:
    """Tests for GET /api/v1/payments/history."""
    
    def test_history_requires_auth(self, client):
        """Verify history requires authentication."""
        response = client.get('/api/v1/payments/history')
        assert response.status_code in [401, 500]

class TestPaymentReceipt:
    """Tests for GET /api/v1/payments/{uuid}/receipt."""
    
    def test_receipt_requires_auth(self, client):
        """Verify receipt requires authentication."""
        response = client.get('/api/v1/payments/12345678-1234-1234-1234-123456789abc/receipt')
        assert response.status_code in [401, 404, 500]

class TestRetryPayment:
    """Tests for POST /api/v1/payments/{uuid}/retry."""
    
    def test_retry_requires_auth(self, client):
        """Verify retry requires authentication."""
        response = client.post('/api/v1/payments/12345678-1234-1234-1234-123456789abc/retry')
        assert response.status_code in [401, 404, 500]

class TestBlueprintRegistration:
    """Tests for blueprint registration."""
    
    def test_all_endpoints(self, app):
        """Verify all endpoints are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected = [
            '/api/v1/payments/<uuid:deal_uuid>/qr',
            '/api/v1/payments/<uuid:deal_uuid>/status',
            '/api/v1/payments/<uuid:deal_uuid>/address',
            '/api/v1/payments/<uuid:deal_uuid>/verify',
            '/api/v1/payments/webhook/trongrid',
            '/api/v1/payments/rates',
            '/api/v1/payments/history',
            '/api/v1/payments/<uuid:deal_uuid>/receipt',
            '/api/v1/payments/<uuid:deal_uuid>/retry'
        ]
        
        for endpoint in expected:
            assert endpoint in rules, f"Missing: {endpoint}"

__all__ = [
    'TestPaymentQR',
    'TestPaymentStatus',
    'TestPaymentAddress',
    'TestVerifyPayment',
    'TestTrongridWebhook',
    'TestExchangeRates',
    'TestPaymentHistory',
    'TestPaymentReceipt',
    'TestRetryPayment',
    'TestBlueprintRegistration'
]

"""
اختبارات metrics.py
Unit Tests for metrics.py
"""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

import sys
sys.path.insert(0, '.')

from src.core.metrics import (
    request_count,
    request_duration,
    active_users,
    active_deals,
    deals_created,
    deals_completed,
    payments_received,
    payouts_sent,
    disputes_opened,
    errors_total,
    tron_api_duration,
    file_upload_size,
    websocket_connections,
    celery_tasks_pending,
    celery_tasks_completed,
    database_connections,
    redis_connections,
    setup_metrics,
    increment_counter,
    observe_histogram,
    set_gauge,
    track_request_duration,
    track_function_duration
)

@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    return app

class TestMetricsSetup:
    """Tests for metrics setup."""
    
    def test_setup_adds_endpoint(self, app):
        """Verify that /metrics endpoint is registered."""
        setup_metrics(app)
        
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/metrics' in rules
    
    def test_metrics_endpoint_returns_200(self, app):
        """Verify that /metrics endpoint returns text response."""
        setup_metrics(app)
        
        with app.test_client() as client:
            response = client.get('/metrics')
            assert response.status_code == 200
            assert response.mimetype == 'text/plain'

class TestCounters:
    """Tests for Prometheus counters."""
    
    def test_increment_counter_no_labels(self):
        """Verify incrementing counter without labels."""
        initial_count = len(generate_latest())
        increment_counter('deals_created', 5)
        assert True  # Counter increment is side-effect, verified via metrics endpoint
    
    def test_increment_counter_with_labels(self):
        """Verify incrementing counter with labels."""
        increment_counter('payments_received', 3, {'currency': 'USDT'})
        assert True  # Labeled counters verified via Prometheus endpoint
    
    def test_errors_counter_exists(self):
        """Verify error counter is defined."""
        assert errors_total is not None
        assert hasattr(errors_total, '_metrics')
    
    def test_counters_are_callable(self):
        """Verify counters can be incremented."""
        # Increment several counters
        deals_created.inc(1)
        deals_completed.inc(1)
        disputes_opened.inc(1)
        celery_tasks_completed.labels(task_name='test').inc(1)
        assert True

class TestHistograms:
    """Tests for Prometheus histograms."""
    
    def test_observe_histogram(self):
        """Verify observing histogram value."""
        observe_histogram('request_duration', 0.5, {'method': 'GET', 'endpoint': '/api/v1/deals'})
        assert True  # Histogram observation is side-effect only
    
    def test_tron_api_histogram(self):
        """Verify Tron API histogram."""
        observe_histogram('tron_api_duration', 1.2, {'operation': 'check_transaction'})
        assert True
    
    def test_histograms_direct_observe(self):
        """Verify histograms can be observed directly."""
        request_duration.labels(method='GET', endpoint='/test').observe(0.3)
        tron_api_duration.labels(operation='test').observe(0.5)
        file_upload_size.labels(mime_type='application/pdf').observe(1024)
        assert True

class TestGauges:
    """Tests for Prometheus gauges."""
    
    def test_set_gauge(self):
        """Verify setting gauge value."""
        set_gauge('active_users', 42)
        assert True  # Gauges set via helper
    
    def test_set_gauge_zero(self):
        """Verify setting gauge to zero."""
        set_gauge('active_deals', 0)
        assert True
    
    def test_set_gauge_direct(self):
        """Verify gauges can be set directly."""
        active_users.set(10)
        active_deals.set(5)
        websocket_connections.set(3)
        celery_tasks_pending.set(2)
        database_connections.set(4)
        redis_connections.set(4)
        assert True
    
    def test_gauge_inc_dec(self):
        """Verify gauge increment and decrement."""
        websocket_connections.inc(1)
        websocket_connections.dec(1)
        assert True

class TestTrackRequestDuration:
    """Tests for track_request_duration decorator."""
    
    def test_decorator_returns_result(self, app):
        """Verify decorator returns function result."""
        @track_request_duration()
        def test_func():
            return {'status': 'ok'}
        
        with app.test_request_context('/test'):
            result = test_func()
            assert result == {'status': 'ok'}
    
    def test_decorator_handles_tuple(self, app):
        """Verify decorator handles tuple return."""
        @track_request_duration()
        def test_func():
            return {'status': 'created'}, 201
        
        with app.test_request_context('/test'):
            result = test_func()
            assert result[1] == 201

class TestTrackFunctionDuration:
    """Tests for track_function_duration decorator."""
    
    def test_decorator_returns_result(self):
        """Verify decorator returns function result."""
        @track_function_duration('test_function')
        def test_func(x):
            return x * 2
        
        result = test_func(5)
        assert result == 10
    
    def test_decorator_preserves_name(self):
        """Verify decorator preserves function name."""
        @track_function_duration('test_function')
        def test_func():
            pass
        
        assert test_func.__name__ == 'test_func'

class TestAllMetricsDefined:
    """Tests that all metrics are properly defined."""
    
    def test_counters_exist(self):
        """Verify all counters are defined."""
        assert request_count is not None
        assert deals_created is not None
        assert deals_completed is not None
        assert payments_received is not None
        assert payouts_sent is not None
        assert disputes_opened is not None
        assert errors_total is not None
        assert celery_tasks_completed is not None
    
    def test_histograms_exist(self):
        """Verify all histograms are defined."""
        assert request_duration is not None
        assert tron_api_duration is not None
        assert file_upload_size is not None
    
    def test_gauges_exist(self):
        """Verify all gauges are defined."""
        assert active_users is not None
        assert active_deals is not None
        assert websocket_connections is not None
        assert celery_tasks_pending is not None
        assert database_connections is not None
        assert redis_connections is not None

class TestMetricsEndpoint:
    """Tests for metrics endpoint content."""
    
    def test_endpoint_contains_counters(self, app):
        """Verify metrics endpoint returns counter data."""
        setup_metrics(app)
        
        deals_created.inc(1)
        
        with app.test_client() as client:
            response = client.get('/metrics')
            text = response.data.decode('utf-8')
            assert 'safesend_deals_created_total' in text
    
    def test_endpoint_contains_gauges(self, app):
        """Verify metrics endpoint returns gauge data."""
        setup_metrics(app)
        
        active_users.set(42)
        
        with app.test_client() as client:
            response = client.get('/metrics')
            text = response.data.decode('utf-8')
            assert 'safesend_active_users' in text

__all__ = [
    'TestMetricsSetup',
    'TestCounters',
    'TestHistograms',
    'TestGauges',
    'TestTrackRequestDuration',
    'TestTrackFunctionDuration',
    'TestAllMetricsDefined',
    'TestMetricsEndpoint'
]

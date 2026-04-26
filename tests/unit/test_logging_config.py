"""
اختبارات نظام التسجيل
Unit Tests for Logging Configuration
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import json
import logging
import tempfile
import uuid
from unittest.mock import patch

import pytest

from src.app.models.logging_config import (
    set_trace_id,
    get_trace_id,
    set_request_context,
    clear_request_context,
    SensitiveDataFilter,
    JSONFormatter,
    StructuredLogger,
    setup_logging,
    get_logger,
    log_error,
    log_security_event,
    trace_id_var,
    user_id_var,
)


class TestContextVariables:
    def test_set_trace_id_generates_new_id(self):
        trace_id = set_trace_id()
        assert trace_id is not None
        uuid.UUID(trace_id)
    
    def test_get_trace_id_returns_none_when_not_set(self):
        clear_request_context()
        assert get_trace_id() is None
    
    def test_set_request_context(self):
        set_request_context(user_id="user-123", ip_address="192.168.1.1")
        assert user_id_var.get() == "user-123"
    
    def test_clear_request_context(self):
        set_request_context(user_id="user-123")
        clear_request_context()
        assert user_id_var.get() is None


class TestSensitiveDataFilter:
    def test_masks_password(self):
        filter_obj = SensitiveDataFilter()
        text = 'password: "secret123"'
        record = logging.LogRecord("test", logging.INFO, "", 0, text, (), None)
        filter_obj.filter(record)
        assert "secret123" not in record.msg
    
    def test_masks_bearer_token(self):
        filter_obj = SensitiveDataFilter()
        text = 'Bearer abc123xyz'
        record = logging.LogRecord("test", logging.INFO, "", 0, text, (), None)
        filter_obj.filter(record)
        assert "abc123xyz" not in record.msg


class TestJSONFormatter:
    def test_format_returns_valid_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "Test", (), None)
        record.trace_id = "trace-123"
        record.user_id = "user-456"
        record.ip_address = "127.0.0.1"
        
        result = formatter.format(record)
        parsed = json.loads(result)
        assert parsed["trace_id"] == "trace-123"
        assert parsed["user_id"] == "user-456"


class TestStructuredLogger:
    def test_security_method(self):
        logger = get_logger("test")
        with patch.object(logger, 'info') as mock_info:
            logger.security("login", user_id="user-1", success=True)
            assert mock_info.called


class TestSetupLogging:
    def test_setup_creates_handlers(self):
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(log_dir=log_dir, enable_console=False, enable_file=True)
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) >= 1
            root_logger.handlers.clear()


class TestIntegration:
    def test_trace_id_in_log(self):
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(log_dir=log_dir, enable_console=False, enable_file=True, json_format=True)
            set_trace_id("test-trace-abc")
            set_request_context(user_id="test-user")
            
            logger = get_logger("test")
            logger.info("Hello")
            
            root_logger = logging.getLogger()
            for h in root_logger.handlers:
                h.flush()
                h.close()
            
            log_file = os.path.join(log_dir, "nexus.log")
            with open(log_file, 'r') as f:
                content = f.read()
                assert "test-trace-abc" in content
                assert "test-user" in content
            
            root_logger.handlers.clear()
            clear_request_context()

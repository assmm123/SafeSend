"""
تكوين نظام التسجيل المتقدم
Advanced Logging Configuration
"""

import json
import logging
import logging.handlers
import os
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set


# ============================================
# Context Variables - متغيرات السياق
# ============================================

trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
ip_address_var: ContextVar[Optional[str]] = ContextVar("ip_address", default=None)


def set_trace_id(trace_id: Optional[str] = None) -> str:
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> Optional[str]:
    return trace_id_var.get()


def set_request_context(user_id: str = None, ip_address: str = None) -> None:
    if user_id:
        user_id_var.set(user_id)
    if ip_address:
        ip_address_var.set(ip_address)


def clear_request_context() -> None:
    trace_id_var.set(None)
    user_id_var.set(None)
    ip_address_var.set(None)


# ============================================
# Sensitive Data Filter
# ============================================

class SensitiveDataFilter(logging.Filter):
    SENSITIVE_PATTERNS = [
        (re.compile(r'"password"\s*:\s*"[^"]*"', re.IGNORECASE), '"password": "***REDACTED***"'),
        (re.compile(r'password\s*[:=]\s*"[^"]*"', re.IGNORECASE), 'password: "***REDACTED***"'),
        (re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+'), 'Bearer ***REDACTED***'),
        (re.compile(r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b'), '***CC-REDACTED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


# ============================================
# Context LogRecord Factory
# ============================================

old_factory = logging.getLogRecordFactory()

def context_log_record_factory(*args, **kwargs):
    """تخصيص LogRecord لإضافة trace_id مباشرة"""
    record = old_factory(*args, **kwargs)
    record.trace_id = trace_id_var.get() or "N/A"
    record.user_id = user_id_var.get() or "N/A"
    record.ip_address = ip_address_var.get() or "N/A"
    return record

logging.setLogRecordFactory(context_log_record_factory)


# ============================================
# JSON Formatter
# ============================================

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "N/A"),
            "user_id": getattr(record, "user_id", "N/A"),
            "ip_address": getattr(record, "ip_address", "N/A"),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


# ============================================
# Structured Logger
# ============================================

class StructuredLogger(logging.Logger):
    def security(self, event: str, user_id: str = None, ip_address: str = None, success: bool = True):
        self.info(f"SECURITY: {event} - success={success}")
    
    def audit(self, action: str, resource: str, resource_id: str = None):
        self.info(f"AUDIT: {action} on {resource} id={resource_id}")
    
    def performance(self, operation: str, duration_ms: float):
        self.info(f"PERFORMANCE: {operation} took {duration_ms:.2f}ms")


logging.setLoggerClass(StructuredLogger)


# ============================================
# Setup
# ============================================

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "./logs",
    enable_console: bool = True,
    enable_file: bool = True,
    json_format: bool = False,
) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    
    root_logger.addFilter(SensitiveDataFilter())
    
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - [%(levelname)s] - %(name)s - "
            "[trace_id=%(trace_id)s] [user_id=%(user_id)s] - "
            "%(message)s"
        )
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    if enable_file:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "nexus.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> StructuredLogger:
    logger = logging.getLogger(name)
    if not isinstance(logger, StructuredLogger):
        logger.__class__ = StructuredLogger
    return logger


def log_error(logger: logging.Logger, error: Exception):
    logger.error(f"Error: {error.__class__.__name__} - {str(error)}", exc_info=True)


def log_security_event(logger: logging.Logger, event: str, user_id: str = None, success: bool = True):
    if isinstance(logger, StructuredLogger):
        logger.security(event, user_id, success=success)
    else:
        logger.info(f"SECURITY: {event} - success={success}")


__all__ = [
    "set_trace_id",
    "get_trace_id",
    "set_request_context",
    "clear_request_context",
    "SensitiveDataFilter",
    "JSONFormatter",
    "StructuredLogger",
    "setup_logging",
    "get_logger",
    "log_error",
    "log_security_event",
]

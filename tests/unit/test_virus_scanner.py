"""
اختبارات خدمة فحص الفيروسات
Unit Tests for Virus Scanner Service
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.virus_scanner import (
    VirusScanner,
    ScanResult,
    HealthStatus,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def scanner_disabled():
    return VirusScanner(enabled=False)


@pytest.fixture
def scanner_enabled():
    return VirusScanner(enabled=True)


@pytest.fixture
def sample_file(temp_dir):
    file_path = Path(temp_dir) / "test.txt"
    file_path.write_text("EICAR-STANDARD-ANTIVIRUS-TEST-FILE")
    return str(file_path)


class TestVirusScannerBasic:
    """اختبارات أساسية"""
    
    def test_disabled_scanner(self, scanner_disabled):
        assert scanner_disabled.enabled is False
        assert scanner_disabled.get_status() == "disabled"
    
    def test_enabled_scanner(self, scanner_enabled):
        assert scanner_enabled.enabled is True
    
    def test_get_status(self, scanner_disabled, scanner_enabled):
        assert scanner_disabled.get_status() == "disabled"
        assert scanner_enabled.get_status() in ["daemon_available", "scan_available", "unavailable"]


class TestScanResult:
    """اختبارات ScanResult"""
    
    def test_scan_result_clean(self):
        result = ScanResult(is_clean=True, is_infected=False, status="clean")
        assert result.is_clean is True
        assert result.is_infected is False
    
    def test_scan_result_infected(self):
        result = ScanResult(is_clean=False, is_infected=True, virus_name="TestVirus", status="infected")
        assert result.is_infected is True
        assert result.virus_name == "TestVirus"
    
    def test_scan_result_serialization(self):
        result = ScanResult(is_clean=True, is_infected=False, status="clean")
        json_str = result.to_json()
        restored = ScanResult.from_json(json_str)
        assert restored.is_clean == result.is_clean


class TestVirusScannerScan:
    """اختبارات الفحص"""
    
    def test_scan_disabled(self, scanner_disabled, sample_file):
        result = scanner_disabled.scan_file(sample_file)
        assert result.status == "skipped"
        assert "disabled" in result.message.lower()
    
    def test_scan_file_not_found(self, scanner_enabled):
        result = scanner_enabled.scan_file("/nonexistent/file.txt")
        assert result.status == "error"
        assert "not found" in result.message.lower()
    
    @patch('src.services.virus_scanner.VirusScanner.is_available')
    def test_scan_unavailable(self, mock_available, scanner_enabled, sample_file):
        mock_available.return_value = False
        result = scanner_enabled.scan_file(sample_file)
        assert result.status == "skipped"
    
    def test_scan_stream(self, scanner_disabled, temp_dir):
        result = scanner_disabled.scan_stream(b"test data", "test.txt")
        assert result.status == "skipped"


class TestVirusScannerHealth:
    """اختبارات الصحة"""
    
    def test_health_check_disabled(self, scanner_disabled):
        health = scanner_disabled.health_check()
        assert health.status == "disabled"
    
    @patch('src.services.virus_scanner.VirusScanner.is_daemon_available')
    @patch('src.services.virus_scanner.VirusScanner.is_scan_available')
    def test_health_check_healthy(self, mock_scan, mock_daemon, scanner_enabled):
        mock_daemon.return_value = True
        mock_scan.return_value = False
        health = scanner_enabled.health_check()
        assert health.status == "healthy"
    
    def test_get_metrics(self, scanner_enabled):
        metrics = scanner_enabled.get_metrics()
        assert "enabled" in metrics
        assert "status" in metrics


class TestVirusScannerCache:
    """اختبارات التخزين المؤقت"""
    
    def test_cache_key_generation(self, scanner_enabled):
        key = scanner_enabled._get_cache_key("test_checksum")
        assert key.startswith("virus:scan:")
    
    def test_check_cache_no_redis(self, scanner_enabled):
        result = scanner_enabled._check_cache("test_checksum")
        assert result is None


__all__ = [
    "TestVirusScannerBasic",
    "TestScanResult",
    "TestVirusScannerScan",
    "TestVirusScannerHealth",
    "TestVirusScannerCache",
]

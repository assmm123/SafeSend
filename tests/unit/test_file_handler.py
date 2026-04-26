"""
اختبارات خدمة معالجة الملفات
Unit Tests for File Handler Service
"""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from PIL import Image, ImageDraw

from src.services.file_handler import (
    FileHandler,
    FileUploadResult,
    FileValidationResult,
    FileTooLargeError,
    InvalidFileTypeError,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def file_handler(temp_dir):
    return FileHandler(upload_dir=temp_dir, enable_virus_scan=False, enable_encryption=False)


@pytest.fixture
def sample_image(temp_dir):
    image_path = Path(temp_dir) / "test_image.jpg"
    img = Image.new('RGB', (800, 600), color='blue')
    img.save(image_path)
    return str(image_path)


@pytest.fixture
def sample_text(temp_dir):
    text_path = Path(temp_dir) / "test.txt"
    text_path.write_text("Hello, World!")
    return str(text_path)


class TestFileSanitization:
    def test_sanitize_filename(self, file_handler):
        name = file_handler.sanitize_filename("My Document (1).pdf")
        assert ".pdf" in name
        assert "(" not in name
    
    def test_detect_double_extension(self, file_handler):
        assert file_handler.detect_double_extension("image.jpg.exe") is True
        assert file_handler.detect_double_extension("doc.pdf.php") is True
        assert file_handler.detect_double_extension("normal.jpg") is False
    
    def test_sanitize_removes_dotdot(self, file_handler):
        name = file_handler.sanitize_filename("../../../etc/passwd")
        assert ".." not in name


class TestFileChecksum:
    def test_calculate_checksum(self, file_handler, sample_text):
        cs1 = file_handler.calculate_checksum(sample_text)
        cs2 = file_handler.calculate_checksum(sample_text)
        assert cs1 == cs2
        assert len(cs1) == 64
    
    def test_calculate_entropy(self, file_handler, sample_text):
        entropy = file_handler.calculate_entropy(sample_text)
        assert 0 <= entropy <= 8


class TestFileTypeDetection:
    def test_detect_true_file_type(self, file_handler, sample_image):
        true_type = file_handler.detect_true_file_type(sample_image)
        assert true_type == '.jpg'
    
    def test_detect_polyglot(self, file_handler, sample_image):
        is_polyglot = file_handler.detect_polyglot_file(sample_image)
        assert is_polyglot is False


class TestFileValidation:
    def test_validate_file_valid(self, file_handler, sample_image):
        result = file_handler.validate_file(sample_image, "test.jpg")
        assert result.valid is True
        assert result.true_extension == '.jpg'
        assert len(result.checksum) == 64
    
    def test_validate_blocked_extension(self, file_handler, sample_text):
        result = file_handler.validate_file(sample_text, "test.exe")
        assert result.valid is False
        assert "Blocked extension" in result.errors[0]
    
    def test_validate_double_extension_warning(self, file_handler, sample_image):
        result = file_handler.validate_file(sample_image, "image.jpg.php")
        assert "Double extension detected" in result.warnings


class TestFileUpload:
    def test_save_uploaded_file_success(self, file_handler, sample_image):
        with open(sample_image, 'rb') as f:
            data = f.read()
        
        result = file_handler.save_uploaded_file(data, "test.jpg")
        assert result.success is True
        assert result.file_id.startswith("file_")
        assert os.path.exists(result.saved_path)
    
    def test_save_uploaded_file_invalid_type(self, file_handler):
        result = file_handler.save_uploaded_file(b"#!/bin/bash", "script.sh")
        assert result.success is False


class TestChunkedUpload:
    def test_save_chunk(self, file_handler):
        result = file_handler.save_chunk(b"chunk1", "upload_123", 0, 3, "large.mp4")
        assert result["success"] is True
        assert result["received"] == 1
        assert result["complete"] is False
    
    def test_assemble_chunks(self, file_handler):
        uid = "assemble_test"
        file_handler.save_chunk(b"CHUNK0", uid, 0, 3, "test.dat")
        file_handler.save_chunk(b"CHUNK1", uid, 1, 3, "test.dat")
        file_handler.save_chunk(b"CHUNK2", uid, 2, 3, "test.dat")
        
        path = file_handler.assemble_chunks(uid)
        assert path is not None
        assert os.path.exists(path)


class TestDownloadTokens:
    def test_generate_token(self, file_handler):
        token = file_handler.generate_download_token("file_123", "user_456")
        assert token.startswith("dl_")
    
    def test_verify_invalid_token(self, file_handler):
        result = file_handler.verify_download_token("invalid")
        assert result is None


class TestCleanup:
    def test_cleanup_temp_files(self, file_handler, sample_image):
        shutil.copy(sample_image, file_handler.temp_dir / "test.jpg")
        deleted = file_handler.cleanup_temp_files(max_age_hours=0)
        assert deleted >= 1


class TestHealthCheck:
    def test_health_check(self, file_handler):
        health = file_handler.health_check()
        assert health["status"] == "healthy"
        assert "upload_dir_writable" in health


import shutil
__all__ = [
    "TestFileSanitization", "TestFileChecksum", "TestFileTypeDetection",
    "TestFileValidation", "TestFileUpload", "TestChunkedUpload",
    "TestDownloadTokens", "TestCleanup", "TestHealthCheck"
]

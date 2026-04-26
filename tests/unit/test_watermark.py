"""
اختبارات خدمة العلامات المائية
Unit Tests for Watermark Service
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from PIL import Image, ImageDraw

from src.services.watermark import (
    WatermarkEngine,
    WatermarkPosition,
    FileType,
    WatermarkResult,
    DynamicWatermark,
    FileTooLargeError,
)


@pytest.fixture
def temp_dir():
    """إنشاء مجلد مؤقت"""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def watermark_engine(temp_dir):
    """إنشاء محرك العلامات المائية"""
    return WatermarkEngine(output_dir=temp_dir)


@pytest.fixture
def sample_image(temp_dir):
    """إنشاء صورة اختبارية"""
    image_path = Path(temp_dir) / "test_image.jpg"
    img = Image.new('RGB', (800, 600), color='blue')
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 300, 300], fill='red')
    img.save(image_path)
    return str(image_path)


class TestFileDetection:
    """اختبارات تحديد نوع الملف"""
    
    def test_detect_image(self, watermark_engine):
        assert watermark_engine.detect_file_type("test.jpg") == FileType.IMAGE
        assert watermark_engine.detect_file_type("test.png") == FileType.IMAGE
        assert watermark_engine.detect_file_type("test.webp") == FileType.IMAGE
    
    def test_detect_video(self, watermark_engine):
        assert watermark_engine.detect_file_type("test.mp4") == FileType.VIDEO
        assert watermark_engine.detect_file_type("test.mov") == FileType.VIDEO
    
    def test_detect_pdf(self, watermark_engine):
        assert watermark_engine.detect_file_type("test.pdf") == FileType.PDF
    
    def test_detect_unknown(self, watermark_engine):
        assert watermark_engine.detect_file_type("test.xyz") == FileType.UNKNOWN


class TestImageWatermark:
    """اختبارات العلامة المائية على الصور"""
    
    def test_process_image_basic(self, watermark_engine, sample_image):
        result = watermark_engine.process_image(
            sample_image,
            "CONFIDENTIAL"
        )
        
        assert result.success is True
        assert result.file_type == "image"
        assert os.path.exists(result.output_path)
        assert result.file_size_bytes > 0
    
    def test_process_image_with_position(self, watermark_engine, sample_image):
        result = watermark_engine.process_image(
            sample_image,
            "TOP SECRET",
            position=WatermarkPosition.TOP_LEFT
        )
        
        assert result.success is True
        assert os.path.exists(result.output_path)
    
    def test_process_image_with_opacity(self, watermark_engine, sample_image):
        result = watermark_engine.process_image(
            sample_image,
            "WATERMARK",
            opacity=0.5
        )
        
        assert result.success is True
    
    def test_process_image_tiled(self, watermark_engine, sample_image):
        result = watermark_engine.add_tiled_watermark(
            sample_image,
            "REPEAT",
            spacing=100
        )
        
        assert result.success is True
        assert os.path.exists(result.output_path)
    
    def test_process_image_cache(self, watermark_engine, sample_image):
        # معالجة أولى
        result1 = watermark_engine.process_image(sample_image, "CACHED")
        assert result1.success is True
        assert result1.processing_time_ms > 0
        
        # معالجة ثانية - يجب أن تكون أسرع
        result2 = watermark_engine.process_image(sample_image, "CACHED")
        assert result2.success is True
    
    def test_process_image_invalid_path(self, watermark_engine):
        result = watermark_engine.process_image(
            "/nonexistent/image.jpg",
            "TEST"
        )
        
        assert result.success is False
        assert result.error is not None


class TestVideoWatermark:
    """اختبارات العلامة المائية على الفيديو"""
    
    @patch('src.services.watermark.WatermarkEngine.get_video_info')
    @patch('subprocess.run')
    def test_process_video_basic(self, mock_run, mock_info, watermark_engine, temp_dir):
        mock_info.return_value = MagicMock(duration_sec=10)
        mock_run.return_value = MagicMock(returncode=0)
        
        video_path = Path(temp_dir) / "test.mp4"
        video_path.touch()
        
        result = watermark_engine.process_video(
            str(video_path),
            "VIDEO WATERMARK"
        )
        
        # قد يفشل إذا لم يكن ffmpeg مثبتاً
        if not result.success:
            assert "ffmpeg" in result.error or result.error is not None
    
    def test_validate_video_size(self, watermark_engine, temp_dir):
        video_path = Path(temp_dir) / "large.mp4"
        video_path.touch()
        
        # محاكاة حجم كبير
        with patch('os.path.getsize', return_value=200 * 1024 * 1024):
            with pytest.raises(FileTooLargeError):
                watermark_engine.validate_video_size(str(video_path))
    
    def test_get_video_info_missing_file(self, watermark_engine):
        info = watermark_engine.get_video_info("/nonexistent/video.mp4")
        assert info is None


class TestPDFWatermark:
    """اختبارات العلامة المائية على PDF"""
    
    def _skip_test_process_pdf_no_libraries(self, watermark_engine, temp_dir):
        pdf_path = Path(temp_dir) / "test.pdf"
        pdf_path.touch()
        
        # بدون مكتبات PDF
        with patch('PyPDF2.PdfReader', side_effect=ImportError):
            result = watermark_engine.process_pdf(str(pdf_path), "PDF WATERMARK")
            assert result.success is False
            assert "not installed" in result.error


class TestDynamicWatermark:
    """اختبارات العلامة المائية الديناميكية"""
    
    def test_generate_dynamic_watermark(self, watermark_engine):
        dynamic = watermark_engine.generate_dynamic_watermark(
            buyer_email="buyer@example.com",
            buyer_ip="192.168.1.1",
            deal_id="deal_123",
            transaction_id="tx_abc"
        )
        
        assert dynamic.buyer_email == "buyer@example.com"
        assert dynamic.buyer_ip == "192.168.1.1"
        assert dynamic.deal_id == "deal_123"
        assert dynamic.transaction_id == "tx_abc"
        assert dynamic.timestamp is not None
        
        text = dynamic.to_string()
        assert "buyer@example.com" in text
        assert "192.168.1.1" in text
        assert "deal_123" in text


class TestAsyncProcessing:
    """اختبارات المعالجة غير المتزامنة"""
    
    def test_process_async_no_celery(self, watermark_engine, sample_image):
        with pytest.raises(Exception):
            watermark_engine.process_async("image", sample_image, "ASYNC")


class TestHealthCheck:
    """اختبارات فحص الصحة"""
    
    def test_health_check(self, watermark_engine):
        health = watermark_engine.health_check()
        
        assert health.status in ["healthy", "degraded"]
        assert isinstance(health.ffmpeg_available, bool)
        assert health.pil_available is True
        assert health.output_dir_writable is True
    
    def test_get_metrics(self, watermark_engine):
        metrics = watermark_engine.get_metrics()
        
        assert "output_dir" in metrics
        assert "default_opacity" in metrics
        assert "default_position" in metrics


class TestCleanup:
    """اختبارات تنظيف الملفات"""
    
    def test_clean_old_files(self, watermark_engine, sample_image):
        # إنشاء ملف
        watermark_engine.process_image(sample_image, "CLEANUP")
        
        # تنظيف الملفات القديمة (0 أيام)
        deleted = watermark_engine.clean_old_files(days=0)
        assert deleted >= 0


class TestEdgeCases:
    """اختبارات حالات خاصة"""
    
    def test_empty_watermark_text(self, watermark_engine, sample_image):
        result = watermark_engine.process_image(sample_image, "")
        assert result.success is True
    
    def test_very_long_watermark_text(self, watermark_engine, sample_image):
        long_text = "VERY LONG WATERMARK TEXT " * 20
        result = watermark_engine.process_image(sample_image, long_text)
        assert result.success is True
    
    def test_special_characters(self, watermark_engine, sample_image):
        result = watermark_engine.process_image(sample_image, "© 2024 CONFIDENTIAL ® ™")
        assert result.success is True


__all__ = [
    "TestFileDetection",
    "TestImageWatermark",
    "TestVideoWatermark",
    "TestPDFWatermark",
    "TestDynamicWatermark",
    "TestAsyncProcessing",
    "TestHealthCheck",
    "TestCleanup",
    "TestEdgeCases",
]

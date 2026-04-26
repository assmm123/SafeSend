"""
خدمة العلامات المائية
Watermark Service

إضافة علامات مائية على الصور والفيديو وPDF لحماية الملفات
- دعم الصور (JPG, PNG, WEBP)
- دعم الفيديو (MP4, MOV)
- دعم PDF
- علامة مائية ديناميكية
- معالجة متزامنة وغير متزامنة
"""

import hashlib
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from src.app.models.helpers import utc_now, generate_id
from src.app.models.logging_config import get_logger

logger = get_logger(__name__)


# ============================================
# الثوابت
# ============================================

class WatermarkPosition(Enum):
    """مواضع العلامة المائية"""
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"
    TILED = "tiled"
    DIAGONAL = "diagonal"


class FileType(Enum):
    """أنواع الملفات المدعومة"""
    IMAGE = "image"
    VIDEO = "video"
    PDF = "pdf"
    UNKNOWN = "unknown"


SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
SUPPORTED_PDF_FORMATS = {'.pdf'}

# حدود Termux
MAX_VIDEO_SIZE_MB = 100
MAX_VIDEO_DURATION_SEC = 300  # 5 دقائق
DEFAULT_WATERMARK_OPACITY = 0.3
DEFAULT_WATERMARK_SIZE_RATIO = 0.1  # 10% من حجم الصورة


# ============================================
# Data Classes
# ============================================

@dataclass
class WatermarkResult:
    """نتيجة إضافة العلامة المائية"""
    success: bool
    input_path: str
    output_path: str
    file_type: str
    watermark_text: str
    processing_time_ms: float
    file_size_bytes: int
    error: Optional[str] = None
    task_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "file_type": self.file_type,
            "watermark_text": self.watermark_text,
            "processing_time_ms": self.processing_time_ms,
            "file_size_bytes": self.file_size_bytes,
            "error": self.error,
            "task_id": self.task_id,
        }


@dataclass
class VideoInfo:
    """معلومات الفيديو"""
    duration_sec: float
    width: int
    height: int
    fps: float
    bitrate: int
    codec: str
    size_bytes: int


@dataclass
class DynamicWatermark:
    """علامة مائية ديناميكية"""
    text: str
    buyer_email: str
    buyer_ip: str
    deal_id: str
    timestamp: str
    transaction_id: str
    
    def to_string(self) -> str:
        lines = [
            f"Buyer: {self.buyer_email}",
            f"IP: {self.buyer_ip}",
            f"Deal: {self.deal_id}",
            f"Time: {self.timestamp}",
            f"Tx: {self.transaction_id[:12]}",
        ]
        return " | ".join(lines)


@dataclass
class HealthStatus:
    """حالة صحة الخدمة"""
    status: str
    ffmpeg_available: bool
    pil_available: bool
    output_dir_writable: bool


# ============================================
# Exceptions
# ============================================

class WatermarkError(Exception):
    """خطأ في معالجة العلامة المائية"""
    pass


class UnsupportedFormatError(WatermarkError):
    """صيغة غير مدعومة"""
    pass


class FileTooLargeError(WatermarkError):
    """الملف كبير جداً"""
    pass


# ============================================
# Watermark Engine
# ============================================

class WatermarkEngine:
    """
    محرك العلامات المائية
    Watermark Engine
    
    يضيف علامات مائية على الصور والفيديو وPDF
    """
    
    def __init__(
        self,
        output_dir: str = "./watermarked",
        celery_app: Any = None,
        redis_client: Any = None,
        default_opacity: float = DEFAULT_WATERMARK_OPACITY,
        default_position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    ):
        """
        تهيئة محرك العلامات المائية
        
        Args:
            output_dir: مجلد المخرجات
            celery_app: تطبيق Celery للمعالجة غير المتزامنة
            redis_client: عميل Redis للتخزين المؤقت
            default_opacity: الشفافية الافتراضية (0.1 - 1.0)
            default_position: الموضع الافتراضي
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.celery_app = celery_app
        self.redis = redis_client
        self.default_opacity = max(0.1, min(1.0, default_opacity))
        self.default_position = default_position
        
        logger.info(f"WatermarkEngine initialized: output_dir={output_dir}")
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def detect_file_type(self, file_path: str) -> FileType:
        """تحديد نوع الملف من الامتداد"""
        ext = Path(file_path).suffix.lower()
        
        if ext in SUPPORTED_IMAGE_FORMATS:
            return FileType.IMAGE
        elif ext in SUPPORTED_VIDEO_FORMATS:
            return FileType.VIDEO
        elif ext in SUPPORTED_PDF_FORMATS:
            return FileType.PDF
        else:
            return FileType.UNKNOWN
    
    def _get_output_path(self, input_path: str, suffix: str = "_watermarked") -> str:
        """توليد مسار المخرج"""
        input_file = Path(input_path)
        output_name = f"{input_file.stem}{suffix}{input_file.suffix}"
        return str(self.output_dir / output_name)
    
    def _get_cache_key(self, input_path: str, text: str) -> str:
        """توليد مفتاح للتخزين المؤقت"""
        data = f"{input_path}:{text}:{os.path.getmtime(input_path)}"
        return f"watermark:{hashlib.sha256(data.encode()).hexdigest()}"
    
    def _check_cache(self, cache_key: str) -> Optional[str]:
        """التحقق من وجود نتيجة في التخزين المؤقت"""
        if self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                logger.info(f"Cache hit: {cache_key}")
                return cached
        return None
    
    def _set_cache(self, cache_key: str, output_path: str, ttl: int = 86400):
        """تخزين النتيجة في التخزين المؤقت"""
        if self.redis:
            self.redis.setex(cache_key, ttl, output_path)
    
    # ============================================
    # التحقق من الملفات
    # ============================================
    
    def validate_video_size(self, file_path: str, max_size_mb: int = MAX_VIDEO_SIZE_MB) -> bool:
        """التحقق من حجم الفيديو"""
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        
        if size_mb > max_size_mb:
            raise FileTooLargeError(f"Video size {size_mb:.1f}MB exceeds limit {max_size_mb}MB")
        
        return True
    
    def get_video_info(self, file_path: str) -> Optional[VideoInfo]:
        """استخراج معلومات الفيديو باستخدام ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-show_format', file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return None
            
            import json
            data = json.loads(result.stdout)
            
            video_stream = next(
                (s for s in data['streams'] if s['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                return None
            
            return VideoInfo(
                duration_sec=float(data['format'].get('duration', 0)),
                width=int(video_stream.get('width', 0)),
                height=int(video_stream.get('height', 0)),
                fps=eval(video_stream.get('r_frame_rate', '0/1')),
                bitrate=int(data['format'].get('bit_rate', 0)),
                codec=video_stream.get('codec_name', 'unknown'),
                size_bytes=int(data['format'].get('size', 0))
            )
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None
    
    def validate_video_duration(self, file_path: str, max_duration_sec: int = MAX_VIDEO_DURATION_SEC) -> bool:
        """التحقق من مدة الفيديو"""
        info = self.get_video_info(file_path)
        if info and info.duration_sec > max_duration_sec:
            raise FileTooLargeError(f"Video duration {info.duration_sec:.0f}s exceeds limit {max_duration_sec}s")
        return True
    
    # ============================================
    # علامة مائية ديناميكية
    # ============================================
    
    def generate_dynamic_watermark(
        self,
        buyer_email: str,
        buyer_ip: str,
        deal_id: str,
        transaction_id: str = ""
    ) -> DynamicWatermark:
        """توليد علامة مائية ديناميكية"""
        return DynamicWatermark(
            text="",
            buyer_email=buyer_email,
            buyer_ip=buyer_ip,
            deal_id=deal_id,
            timestamp=utc_now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            transaction_id=transaction_id
        )
    
    # ============================================
    # معالجة الصور
    # ============================================
    
    def _get_font(self, size: int) -> ImageFont:
        """الحصول على خط مناسب"""
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except:
            try:
                return ImageFont.truetype("/system/fonts/Roboto-Regular.ttf", size)
            except:
                return ImageFont.load_default()
    
    def _calculate_position(
        self,
        position: WatermarkPosition,
        image_size: tuple,
        text_size: tuple,
        margin: int = 20
    ) -> tuple:
        """حساب موضع النص"""
        img_width, img_height = image_size
        text_width, text_height = text_size
        
        positions = {
            WatermarkPosition.TOP_LEFT: (margin, margin),
            WatermarkPosition.TOP_RIGHT: (img_width - text_width - margin, margin),
            WatermarkPosition.BOTTOM_LEFT: (margin, img_height - text_height - margin),
            WatermarkPosition.BOTTOM_RIGHT: (img_width - text_width - margin, img_height - text_height - margin),
            WatermarkPosition.CENTER: ((img_width - text_width) // 2, (img_height - text_height) // 2),
        }
        
        return positions.get(position, positions[WatermarkPosition.BOTTOM_RIGHT])
    
    def process_image(
        self,
        input_path: str,
        watermark_text: str,
        output_path: Optional[str] = None,
        position: WatermarkPosition = None,
        opacity: float = None,
        font_size: Optional[int] = None
    ) -> WatermarkResult:
        """
        إضافة علامة مائية على صورة
        
        Args:
            input_path: مسار الصورة الأصلية
            watermark_text: نص العلامة المائية
            output_path: مسار المخرج (اختياري)
            position: موضع العلامة
            opacity: الشفافية
            font_size: حجم الخط
            
        Returns:
            نتيجة المعالجة
        """
        import time
        start_time = time.time()
        
        try:
            # التحقق من التخزين المؤقت
            cache_key = self._get_cache_key(input_path, watermark_text)
            cached = self._check_cache(cache_key)
            if cached and os.path.exists(cached):
                return WatermarkResult(
                    success=True,
                    input_path=input_path,
                    output_path=cached,
                    file_type="image",
                    watermark_text=watermark_text,
                    processing_time_ms=0,
                    file_size_bytes=os.path.getsize(cached)
                )
            
            if output_path is None:
                output_path = self._get_output_path(input_path)
            
            position = position or self.default_position
            opacity = opacity if opacity is not None else self.default_opacity
            
            # فتح الصورة
            image = Image.open(input_path)
            
            # تحويل إلى RGB إذا لزم
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
            
            # إنشاء طبقة شفافة للنص
            txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            # تحديد حجم الخط
            if font_size is None:
                font_size = int(min(image.size) * DEFAULT_WATERMARK_SIZE_RATIO)
            font = self._get_font(font_size)
            
            # قياس النص
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # حساب الموضع
            x, y = self._calculate_position(position, image.size, (text_width, text_height))
            
            # رسم النص
            alpha = int(255 * opacity)
            draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, alpha))
            
            # دمج الطبقات
            watermarked = Image.alpha_composite(image.convert('RGBA'), txt_layer)
            watermarked = watermarked.convert('RGB')
            
            # حفظ الصورة
            watermarked.save(output_path, quality=95)
            
            processing_time = (time.time() - start_time) * 1000
            file_size = os.path.getsize(output_path)
            
            self._set_cache(cache_key, output_path)
            
            logger.info(f"Image watermarked: {input_path} -> {output_path}")
            
            return WatermarkResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                file_type="image",
                watermark_text=watermark_text,
                processing_time_ms=processing_time,
                file_size_bytes=file_size
            )
            
        except Exception as e:
            logger.error(f"Image watermark failed: {e}")
            return WatermarkResult(
                success=False,
                input_path=input_path,
                output_path="",
                file_type="image",
                watermark_text=watermark_text,
                processing_time_ms=0,
                file_size_bytes=0,
                error=str(e)
            )
    
    def add_tiled_watermark(
        self,
        input_path: str,
        watermark_text: str,
        output_path: Optional[str] = None,
        opacity: float = 0.15,
        spacing: int = 150
    ) -> WatermarkResult:
        """إضافة علامة مائية متكررة"""
        import time
        start_time = time.time()
        
        try:
            if output_path is None:
                output_path = self._get_output_path(input_path, "_tiled")
            
            image = Image.open(input_path).convert('RGBA')
            txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            font_size = int(min(image.size) * 0.05)
            font = self._get_font(font_size)
            
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[0]
            
            alpha = int(255 * opacity)
            
            for x in range(0, image.width, text_width + spacing):
                for y in range(0, image.height, text_height + spacing):
                    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, alpha))
            
            watermarked = Image.alpha_composite(image, txt_layer).convert('RGB')
            watermarked.save(output_path, quality=95)
            
            processing_time = (time.time() - start_time) * 1000
            
            return WatermarkResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                file_type="image",
                watermark_text=watermark_text,
                processing_time_ms=processing_time,
                file_size_bytes=os.path.getsize(output_path)
            )
            
        except Exception as e:
            logger.error(f"Tiled watermark failed: {e}")
            return WatermarkResult(
                success=False,
                input_path=input_path,
                output_path="",
                file_type="image",
                watermark_text=watermark_text,
                processing_time_ms=0,
                file_size_bytes=0,
                error=str(e)
            )
    
    # ============================================
    # معالجة الفيديو
    # ============================================
    
    def process_video(
        self,
        input_path: str,
        watermark_text: str,
        output_path: Optional[str] = None,
        position: WatermarkPosition = None,
        opacity: float = None
    ) -> WatermarkResult:
        """
        إضافة علامة مائية على فيديو
        
        Args:
            input_path: مسار الفيديو الأصلي
            watermark_text: نص العلامة المائية
            output_path: مسار المخرج
            position: موضع العلامة
            opacity: الشفافية
            
        Returns:
            نتيجة المعالجة
        """
        import time
        start_time = time.time()
        
        try:
            # التحقق من الحدود
            self.validate_video_size(input_path)
            self.validate_video_duration(input_path)
            
            # التحقق من التخزين المؤقت
            cache_key = self._get_cache_key(input_path, watermark_text)
            cached = self._check_cache(cache_key)
            if cached and os.path.exists(cached):
                return WatermarkResult(
                    success=True,
                    input_path=input_path,
                    output_path=cached,
                    file_type="video",
                    watermark_text=watermark_text,
                    processing_time_ms=0,
                    file_size_bytes=os.path.getsize(cached)
                )
            
            if output_path is None:
                output_path = self._get_output_path(input_path)
            
            position = position or self.default_position
            opacity = opacity if opacity is not None else self.default_opacity
            
            # تحديد موضع النص
            x_pos = "10"
            y_pos = "10"
            if position == WatermarkPosition.TOP_RIGHT:
                x_pos = "main_w-text_w-10"
            elif position == WatermarkPosition.BOTTOM_LEFT:
                y_pos = "main_h-text_h-10"
            elif position == WatermarkPosition.BOTTOM_RIGHT:
                x_pos = "main_w-text_w-10"
                y_pos = "main_h-text_h-10"
            elif position == WatermarkPosition.CENTER:
                x_pos = "(main_w-text_w)/2"
                y_pos = "(main_h-text_h)/2"
            
            # بناء أمر ffmpeg
            fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            fontsize = 36
            alpha = opacity
            
            drawtext = (
                f"drawtext=text='{watermark_text}':"
                f"fontcolor=white@{alpha}:fontsize={fontsize}:"
                f"x={x_pos}:y={y_pos}"
            )
            
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', drawtext,
                '-c:v', 'libx264', '-crf', '23',
                '-c:a', 'copy',
                '-y', output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise WatermarkError(f"ffmpeg failed: {result.stderr}")
            
            processing_time = (time.time() - start_time) * 1000
            file_size = os.path.getsize(output_path)
            
            self._set_cache(cache_key, output_path)
            
            logger.info(f"Video watermarked: {input_path} -> {output_path}")
            
            return WatermarkResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                file_type="video",
                watermark_text=watermark_text,
                processing_time_ms=processing_time,
                file_size_bytes=file_size
            )
            
        except Exception as e:
            logger.error(f"Video watermark failed: {e}")
            return WatermarkResult(
                success=False,
                input_path=input_path,
                output_path="",
                file_type="video",
                watermark_text=watermark_text,
                processing_time_ms=0,
                file_size_bytes=0,
                error=str(e)
            )
    
    # ============================================
    # معالجة PDF
    # ============================================
    
    def process_pdf(
        self,
        input_path: str,
        watermark_text: str,
        output_path: Optional[str] = None,
        opacity: float = 0.3
    ) -> WatermarkResult:
        """
        إضافة علامة مائية على PDF
        
        Args:
            input_path: مسار PDF الأصلي
            watermark_text: نص العلامة المائية
            output_path: مسار المخرج
            opacity: الشفافية
            
        Returns:
            نتيجة المعالجة
        """
        import time
        start_time = time.time()
        
        try:
            if output_path is None:
                output_path = self._get_output_path(input_path)
            
            # استخدام PyPDF2 أو reportlab
            try:
                from PyPDF2 import PdfReader, PdfWriter
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import inch
                from reportlab.lib.colors import Color
                import io
            except ImportError:
                logger.warning("PDF libraries not available, returning original")
                return WatermarkResult(
                    success=False,
                    input_path=input_path,
                    output_path="",
                    file_type="pdf",
                    watermark_text=watermark_text,
                    processing_time_ms=0,
                    file_size_bytes=0,
                    error="PDF libraries not installed"
                )
            
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            for page in reader.pages:
                packet = io.BytesIO()
                c = canvas.Canvas(packet, pagesize=(page.mediabox.width, page.mediabox.height))
                
                c.setFillColor(Color(0, 0, 0, alpha=opacity))
                c.setFont("Helvetica", 48)
                c.saveState()
                c.translate(page.mediabox.width / 2, page.mediabox.height / 2)
                c.rotate(45)
                c.drawCentredString(0, 0, watermark_text)
                c.restoreState()
                c.save()
                
                packet.seek(0)
                watermark_pdf = PdfReader(packet)
                page.merge_page(watermark_pdf.pages[0])
                writer.add_page(page)
            
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            processing_time = (time.time() - start_time) * 1000
            
            return WatermarkResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                file_type="pdf",
                watermark_text=watermark_text,
                processing_time_ms=processing_time,
                file_size_bytes=os.path.getsize(output_path)
            )
            
        except Exception as e:
            logger.error(f"PDF watermark failed: {e}")
            return WatermarkResult(
                success=False,
                input_path=input_path,
                output_path="",
                file_type="pdf",
                watermark_text=watermark_text,
                processing_time_ms=0,
                file_size_bytes=0,
                error=str(e)
            )
    
    # ============================================
    # معالجة غير متزامنة
    # ============================================
    
    def process_async(
        self,
        file_type: str,
        input_path: str,
        watermark_text: str,
        **kwargs
    ) -> str:
        """
        معالجة غير متزامنة عبر Celery
        
        Args:
            file_type: نوع الملف (image, video, pdf)
            input_path: مسار الملف
            watermark_text: نص العلامة
            **kwargs: معاملات إضافية
            
        Returns:
            task_id
        """
        if not self.celery_app:
            raise WatermarkError("Celery not configured")
        
        task_name = f"watermark.process_{file_type}"
        task = self.celery_app.send_task(
            task_name,
            args=[input_path, watermark_text],
            kwargs=kwargs
        )
        
        logger.info(f"Async watermark task created: {task.id}")
        return task.id
    
    # ============================================
    # الصحة والمراقبة
    # ============================================
    
    def health_check(self) -> HealthStatus:
        """
        فحص صحة الخدمة
        
        Returns:
            حالة الصحة
        """
        # فحص ffmpeg
        ffmpeg_available = False
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
            ffmpeg_available = result.returncode == 0
        except:
            pass
        
        # فحص PIL
        pil_available = True  # مثبت مع التبعيات
        
        # فحص الكتابة
        output_dir_writable = os.access(self.output_dir, os.W_OK)
        
        status = "healthy" if (ffmpeg_available and output_dir_writable) else "degraded"
        
        return HealthStatus(
            status=status,
            ffmpeg_available=ffmpeg_available,
            pil_available=pil_available,
            output_dir_writable=output_dir_writable
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الخدمة
        
        Returns:
            إحصائيات
        """
        return {
            "output_dir": str(self.output_dir),
            "default_opacity": self.default_opacity,
            "default_position": self.default_position.value,
            "ffmpeg_available": self.health_check().ffmpeg_available,
        }
    
    def clean_old_files(self, days: int = 7) -> int:
        """حذف الملفات المؤقتة القديمة"""
        import time
        cutoff = time.time() - (days * 86400)
        deleted = 0
        
        for file in self.output_dir.glob("*_watermarked*"):
            if file.stat().st_mtime < cutoff:
                file.unlink()
                deleted += 1
        
        logger.info(f"Cleaned {deleted} old watermarked files")
        return deleted
    
    def __repr__(self) -> str:
        return f"<WatermarkEngine output_dir={self.output_dir}>"


__all__ = [
    "WatermarkEngine",
    "WatermarkPosition",
    "FileType",
    "WatermarkResult",
    "VideoInfo",
    "DynamicWatermark",
    "HealthStatus",
    "WatermarkError",
    "UnsupportedFormatError",
    "FileTooLargeError",
]

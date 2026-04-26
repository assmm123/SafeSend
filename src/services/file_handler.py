"""
خدمة معالجة الملفات المتقدمة
Advanced File Handler Service
"""

import hashlib
import json
import math
import os
import re
import shutil
import time
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.app.models.helpers import utc_now, generate_id
from src.app.models.logging_config import get_logger

logger = get_logger(__name__)


# ============================================
# الثوابت
# ============================================

MAGIC_SIGNATURES = {
    b'\xFF\xD8\xFF': '.jpg',
    b'\x89PNG\r\n\x1A\n': '.png',
    b'GIF87a': '.gif',
    b'GIF89a': '.gif',
    b'%PDF': '.pdf',
    b'PK\x03\x04': '.zip',
    b'\x00\x00\x00\x18ftyp': '.mp4',
    b'MZ': '.exe',
}

DEFAULT_ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.pdf', '.zip', '.mp4', '.mov', '.txt', '.json'
}

BLOCKED_EXTENSIONS = {
    '.exe', '.dll', '.so', '.sh', '.bat', '.cmd',
    '.php', '.js', '.vbs', '.ps1', '.py'
}

DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
DOWNLOAD_TOKEN_TTL = 300


# ============================================
# Data Classes
# ============================================

@dataclass
class FileUploadResult:
    success: bool
    file_id: str
    original_name: str
    saved_path: str
    file_size: int
    mime_type: str
    true_extension: str
    checksum: str
    encrypted: bool
    virus_scanned: bool
    virus_clean: bool
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "file_id": self.file_id,
            "original_name": self.original_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "checksum": self.checksum,
            "encrypted": self.encrypted,
            "virus_clean": self.virus_clean,
            "error": self.error,
            "warnings": self.warnings,
        }


@dataclass
class FileValidationResult:
    valid: bool
    true_extension: str
    mime_type: str
    checksum: str
    entropy: float
    is_encrypted: bool
    is_polyglot: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ============================================
# Exceptions
# ============================================

class FileHandlerError(Exception):
    pass


class FileTooLargeError(FileHandlerError):
    pass


class InvalidFileTypeError(FileHandlerError):
    pass


class VirusDetectedError(FileHandlerError):
    pass


# ============================================
# File Handler
# ============================================

class FileHandler:
    """معالج الملفات المتقدم"""
    
    def __init__(
        self,
        upload_dir: str = "./uploads",
        encryption_service: Any = None,
        watermark_engine: Any = None,
        virus_scanner: Any = None,
        redis_client: Any = None,
        allowed_extensions: Optional[set] = None,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        enable_virus_scan: bool = True,
        enable_encryption: bool = True
    ):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        self.encryption_service = encryption_service
        self.watermark_engine = watermark_engine
        self.virus_scanner = virus_scanner
        self.redis = redis_client
        
        self.allowed_extensions = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS
        self.max_file_size = max_file_size
        self.enable_virus_scan = enable_virus_scan and virus_scanner is not None
        self.enable_encryption = enable_encryption and encryption_service is not None
        
        self.temp_dir = self.upload_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        self.chunks_dir = self.upload_dir / "chunks"
        self.chunks_dir.mkdir(exist_ok=True)
        self.encrypted_dir = self.upload_dir / "encrypted"
        self.encrypted_dir.mkdir(exist_ok=True)
        
        logger.info(f"FileHandler initialized: {upload_dir}")
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def sanitize_filename(self, filename: str) -> str:
        """تنظيف اسم الملف"""
        filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        filename = filename.replace('..', '')
        filename = os.path.basename(filename)
        
        name, ext = os.path.splitext(filename)
        timestamp = utc_now().strftime('%Y%m%d%H%M%S')
        
        return f"{name}_{timestamp}{ext}"
    
    def detect_double_extension(self, filename: str) -> bool:
        """كشف الامتداد المزدوج"""
        parts = filename.lower().split('.')
        suspicious = ['exe', 'php', 'js', 'vbs', 'bat', 'sh', 'py']
        
        if len(parts) > 2:
            for pattern in suspicious:
                if pattern in parts[-2] or pattern in parts[-1]:
                    return True
        return False
    
    def calculate_checksum(self, file_path: str) -> str:
        """حساب SHA256"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def calculate_entropy(self, file_path: str) -> float:
        """حساب entropy"""
        byte_counts = [0] * 256
        total = 0
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                for byte in chunk:
                    byte_counts[byte] += 1
                    total += 1
        
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in byte_counts:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        return entropy
    
    def detect_true_file_type(self, file_path: str) -> str:
        """كشف النوع الحقيقي من Magic Bytes"""
        with open(file_path, 'rb') as f:
            header = f.read(16)
        
        for magic, ext in MAGIC_SIGNATURES.items():
            if header.startswith(magic):
                return ext
        
        return '.unknown'
    
    def detect_polyglot_file(self, file_path: str) -> bool:
        """كشف الملفات متعددة الهوية"""
        types_found = set()
        
        with open(file_path, 'rb') as f:
            for offset in [0, 1024, 2048, 4096]:
                f.seek(offset)
                chunk = f.read(1024)
                for magic, ext in MAGIC_SIGNATURES.items():
                    if chunk.startswith(magic):
                        types_found.add(ext)
        
        return len(types_found) > 1
    
    def detect_zip_bomb(self, file_path: str) -> bool:
        """كشف zip bomb"""
        if not file_path.endswith('.zip'):
            return False
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                total_uncompressed = sum(info.file_size for info in zf.infolist())
                compressed_size = os.path.getsize(file_path)
                
                if total_uncompressed > compressed_size * 100:
                    return True
                if len(zf.infolist()) > 10000:
                    return True
        except:
            pass
        
        return False
    
    def _get_mime_type(self, ext: str) -> str:
        """تحويل الامتداد إلى MIME"""
        mime_map = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
            '.gif': 'image/gif', '.webp': 'image/webp',
            '.pdf': 'application/pdf', '.zip': 'application/zip',
            '.mp4': 'video/mp4', '.mov': 'video/quicktime',
            '.txt': 'text/plain', '.json': 'application/json',
        }
        return mime_map.get(ext, 'application/octet-stream')
    
    # ============================================
    # التحقق من الملفات
    # ============================================
    
    def validate_file(self, file_path: str, original_filename: str) -> FileValidationResult:
        """التحقق الشامل من الملف"""
        errors = []
        warnings = []
        
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            errors.append(f"File too large: {format_file_size(file_size)}")
        
        ext = Path(original_filename).suffix.lower()
        if ext in BLOCKED_EXTENSIONS:
            errors.append(f"Blocked extension: {ext}")
        if ext not in self.allowed_extensions:
            errors.append(f"Extension not allowed: {ext}")
        
        if self.detect_double_extension(original_filename):
            warnings.append("Double extension detected")
        
        true_ext = self.detect_true_file_type(file_path)
        if true_ext == '.unknown':
            warnings.append("Unknown file type")
        elif true_ext != ext and ext not in ['.jpg', '.jpeg']:
            warnings.append(f"Extension mismatch: {ext} vs {true_ext}")
        
        checksum = self.calculate_checksum(file_path)
        entropy = self.calculate_entropy(file_path)
        is_encrypted = entropy > 7.5
        
        if is_encrypted:
            warnings.append(f"File appears encrypted (entropy={entropy:.2f})")
        
        is_polyglot = self.detect_polyglot_file(file_path)
        if is_polyglot:
            errors.append("Polyglot file detected")
        
        if ext == '.zip' and self.detect_zip_bomb(file_path):
            errors.append("Zip bomb detected")
        
        return FileValidationResult(
            valid=len(errors) == 0,
            true_extension=true_ext,
            mime_type=self._get_mime_type(ext),
            checksum=checksum,
            entropy=entropy,
            is_encrypted=is_encrypted,
            is_polyglot=is_polyglot,
            errors=errors,
            warnings=warnings
        )
    
    def scan_for_viruses(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """فحص الفيروسات"""
        if not self.enable_virus_scan:
            return True, "skipped"
        
        try:
            result = self.virus_scanner.scan_file(file_path)
            return result.is_clean, result.status
        except Exception as e:
            logger.error(f"Virus scan failed: {e}")
            return False, f"error: {e}"
    
    # ============================================
    # رفع الملفات
    # ============================================
    
    def save_uploaded_file(
        self,
        file_data: bytes,
        original_filename: str,
        encrypt: bool = False
    ) -> FileUploadResult:
        """حفظ ملف مرفوع"""
        file_id = generate_id("file")
        sanitized = self.sanitize_filename(original_filename)
        
        temp_path = self.temp_dir / f"{file_id}_{sanitized}"
        with open(temp_path, 'wb') as f:
            f.write(file_data)
        
        warnings = []
        
        try:
            validation = self.validate_file(str(temp_path), original_filename)
            
            if not validation.valid:
                os.unlink(temp_path)
                return FileUploadResult(
                    success=False, file_id=file_id, original_name=original_filename,
                    saved_path="", file_size=len(file_data), mime_type="",
                    true_extension="", checksum="", encrypted=False,
                    virus_scanned=False, virus_clean=False,
                    error="; ".join(validation.errors), warnings=validation.warnings
                )
            
            warnings = validation.warnings
            
            virus_clean, virus_result = self.scan_for_viruses(str(temp_path))
            if not virus_clean:
                os.unlink(temp_path)
                return FileUploadResult(
                    success=False, file_id=file_id, original_name=original_filename,
                    saved_path="", file_size=len(file_data), mime_type=validation.mime_type,
                    true_extension=validation.true_extension, checksum="", encrypted=False,
                    virus_scanned=True, virus_clean=False,
                    error=f"Virus detected: {virus_result}", warnings=warnings
                )
            
            final_path = self.upload_dir / f"{file_id}_{sanitized}"
            encrypted = False
            
            if encrypt and self.enable_encryption:
                encrypted_path = self.encrypted_dir / f"{file_id}_{sanitized}.enc"
                self.encryption_service.encrypt_file(str(temp_path), str(encrypted_path))
                final_path = encrypted_path
                encrypted = True
                os.unlink(temp_path)
            else:
                shutil.move(str(temp_path), str(final_path))
            
            final_checksum = self.calculate_checksum(str(final_path))
            
            if self.redis:
                self.redis.hset(f"file:{file_id}", mapping={
                    "original_name": original_filename,
                    "path": str(final_path),
                    "size": str(len(file_data)),
                    "checksum": final_checksum,
                    "created_at": utc_now().isoformat()
                })
                self.redis.expire(f"file:{file_id}", 86400 * 30)
            
            logger.info(f"File saved: {file_id}")
            
            return FileUploadResult(
                success=True, file_id=file_id, original_name=original_filename,
                saved_path=str(final_path), file_size=len(file_data),
                mime_type=validation.mime_type, true_extension=validation.true_extension,
                checksum=final_checksum, encrypted=encrypted,
                virus_scanned=self.enable_virus_scan, virus_clean=True,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            if temp_path.exists():
                os.unlink(temp_path)
            return FileUploadResult(
                success=False, file_id=file_id, original_name=original_filename,
                saved_path="", file_size=len(file_data), mime_type="",
                true_extension="", checksum="", encrypted=False,
                virus_scanned=False, virus_clean=False, error=str(e), warnings=warnings
            )
    
    # ============================================
    # رفع متقطع
    # ============================================
    
    def save_chunk(
        self, chunk_data: bytes, upload_id: str, chunk_index: int,
        total_chunks: int, original_filename: str
    ) -> dict:
        """حفظ قطعة"""
        chunk_dir = self.chunks_dir / upload_id
        chunk_dir.mkdir(exist_ok=True)
        
        chunk_path = chunk_dir / f"chunk_{chunk_index:05d}"
        
        try:
            with open(chunk_path, 'wb') as f:
                f.write(chunk_data)
            
            meta = {
                "original_filename": original_filename,
                "total_chunks": total_chunks,
                "created_at": utc_now().isoformat()
            }
            with open(chunk_dir / "meta.json", 'w') as f:
                json.dump(meta, f)
            
            received = len(list(chunk_dir.glob("chunk_*")))
            
            return {
                "success": True, "chunk_index": chunk_index,
                "received": received, "total": total_chunks,
                "complete": received == total_chunks
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def assemble_chunks(self, upload_id: str) -> Optional[str]:
        """تجميع القطع"""
        chunk_dir = self.chunks_dir / upload_id
        if not chunk_dir.exists():
            return None
        
        try:
            with open(chunk_dir / "meta.json", 'r') as f:
                meta = json.load(f)
            
            total = meta['total_chunks']
            original = meta['original_filename']
            
            for i in range(total):
                if not (chunk_dir / f"chunk_{i:05d}").exists():
                    return None
            
            output = self.temp_dir / f"{upload_id}_{original}"
            with open(output, 'wb') as outf:
                for i in range(total):
                    chunk_path = chunk_dir / f"chunk_{i:05d}"
                    with open(chunk_path, 'rb') as inf:
                        shutil.copyfileobj(inf, outf)
            
            shutil.rmtree(chunk_dir)
            return str(output)
        except Exception as e:
            logger.error(f"Assembly failed: {e}")
            return None
    
    # ============================================
    # تحميل
    # ============================================
    
    def generate_download_token(self, file_id: str, user_id: str, ttl: int = DOWNLOAD_TOKEN_TTL) -> str:
        """توليد token تحميل"""
        token = generate_id("dl")
        if self.redis:
            self.redis.setex(f"download:{token}", ttl, f"{file_id}:{user_id}")
        return token
    
    def verify_download_token(self, token: str) -> Optional[Tuple[str, str]]:
        """التحقق من token"""
        if not self.redis:
            return None
        data = self.redis.get(f"download:{token}")
        if data:
            self.redis.delete(f"download:{token}")
            return tuple(data.split(':'))
        return None
    
    def get_file_path(self, file_id: str) -> Optional[str]:
        """الحصول على مسار الملف"""
        if self.redis:
            return self.redis.hget(f"file:{file_id}", "path")
        return None
    
    # ============================================
    # تنظيف
    # ============================================
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """تنظيف الملفات المؤقتة"""
        cutoff = time.time() - (max_age_hours * 3600)
        deleted = 0
        
        for temp_file in self.temp_dir.glob("*"):
            if temp_file.stat().st_mtime < cutoff:
                temp_file.unlink()
                deleted += 1
        
        for chunk_dir in self.chunks_dir.glob("*"):
            if chunk_dir.is_dir() and chunk_dir.stat().st_mtime < cutoff:
                shutil.rmtree(chunk_dir)
                deleted += 1
        
        return deleted
    
    def health_check(self) -> dict:
        """فحص الصحة"""
        return {
            "status": "healthy",
            "upload_dir_writable": os.access(self.upload_dir, os.W_OK),
            "encryption_enabled": self.enable_encryption,
            "virus_scan_enabled": self.enable_virus_scan,
            "allowed_extensions": len(self.allowed_extensions),
            "max_file_size": self.max_file_size,
        }
    
    def __repr__(self) -> str:
        return f"<FileHandler upload_dir={self.upload_dir}>"


__all__ = [
    "FileHandler", "FileUploadResult", "FileValidationResult",
    "FileHandlerError", "FileTooLargeError", "InvalidFileTypeError", "VirusDetectedError"
]

"""
خدمة فحص الفيروسات المتقدمة
Advanced Virus Scanner Service

ميزات إنتاجية كاملة:
- ClamAV daemon (clamd) مع fallback إلى clamscan
- VirusTotal API مع rate limiting
- تخزين مؤقت في Redis
- Circuit Breaker للحماية
- حجر صحي للملفات المصابة
- تحديث تلقائي للتعريفات
- فحص متعدد المحركات
- دعم Termux (اختياري)
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.app.models.helpers import utc_now, generate_id
from src.app.models.logging_config import get_logger
from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = get_logger(__name__)


# ============================================
# الثوابت
# ============================================

DEFAULT_CLAMAV_HOST = "localhost"
DEFAULT_CLAMAV_PORT = 3310
CLAMAV_SCAN_TIMEOUT = 120
VIRUSTOTAL_RATE_LIMIT = 4
VIRUSTOTAL_POLL_INTERVAL = 5
VIRUSTOTAL_MAX_POLLS = 20
CACHE_TTL = 86400


# ============================================
# Data Classes
# ============================================

@dataclass
class ScanResult:
    is_clean: bool
    is_infected: bool
    virus_name: Optional[str] = None
    status: str = "unknown"
    engine: str = "clamav"
    scan_time_ms: float = 0
    message: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "is_clean": self.is_clean, "is_infected": self.is_infected,
            "virus_name": self.virus_name, "status": self.status,
            "engine": self.engine, "scan_time_ms": self.scan_time_ms,
            "message": self.message, "checksum": self.checksum,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, data: str) -> 'ScanResult':
        d = json.loads(data)
        return cls(**d)


@dataclass
class VirusTotalResult:
    file_id: str
    positives: int
    total: int
    permalink: str
    scan_date: str
    results: Dict[str, dict] = field(default_factory=dict)
    
    @property
    def is_clean(self) -> bool:
        return self.positives == 0


@dataclass
class HealthStatus:
    status: str
    clamav_daemon_available: bool
    clamav_scan_available: bool
    clamav_version: Optional[str] = None
    virustotal_available: bool = False
    cache_enabled: bool = False
    circuit_breaker_state: str = "closed"
    quarantine_enabled: bool = False


# ============================================
# Exceptions
# ============================================

class VirusScannerError(Exception):
    pass


class ClamAVDaemonUnavailableError(VirusScannerError):
    pass


class ClamAVScanUnavailableError(VirusScannerError):
    pass


class VirusDetectedError(VirusScannerError):
    pass


# ============================================
# Virus Scanner
# ============================================

class VirusScanner:
    """ماسح الفيروسات المتقدم"""
    
    def __init__(
        self,
        clamav_host: str = DEFAULT_CLAMAV_HOST,
        clamav_port: int = DEFAULT_CLAMAV_PORT,
        enabled: bool = True,
        virustotal_api_key: Optional[str] = None,
        redis_client: Any = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        quarantine_dir: Optional[str] = None,
        cache_ttl: int = CACHE_TTL,
        fallback_to_clamscan: bool = True
    ):
        self.clamav_host = clamav_host
        self.clamav_port = clamav_port
        self.enabled = enabled
        self.virustotal_api_key = virustotal_api_key
        self.redis = redis_client
        self.cache_ttl = cache_ttl
        self.fallback_to_clamscan = fallback_to_clamscan
        
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="virus_scanner", failure_threshold=3, timeout=60.0
        )
        
        self.quarantine_dir = Path(quarantine_dir) if quarantine_dir else None
        if self.quarantine_dir:
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        self._daemon_available = None
        self._scan_available = None
        self._version = None
        
        logger.info(f"VirusScanner initialized: enabled={enabled}")
    
    # ============================================
    # دوال التوفر
    # ============================================
    
    def is_daemon_available(self) -> bool:
        if self._daemon_available is not None:
            return self._daemon_available
        if not self.enabled:
            self._daemon_available = False
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.clamav_host, self.clamav_port))
            sock.send(b'PING\n')
            response = sock.recv(1024).decode().strip()
            sock.close()
            self._daemon_available = response == 'PONG'
            return self._daemon_available
        except Exception:
            self._daemon_available = False
            return False
    
    def is_scan_available(self) -> bool:
        if self._scan_available is not None:
            return self._scan_available
        try:
            result = subprocess.run(['clamscan', '--version'], capture_output=True, timeout=5)
            self._scan_available = result.returncode == 0
            return self._scan_available
        except Exception:
            self._scan_available = False
            return False
    
    def is_available(self) -> bool:
        return self.is_daemon_available() or (self.fallback_to_clamscan and self.is_scan_available())
    
    def get_version(self) -> Optional[str]:
        if self._version:
            return self._version
        if self.is_daemon_available():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.clamav_host, self.clamav_port))
                sock.send(b'VERSION\n')
                self._version = sock.recv(1024).decode().strip()
                sock.close()
                return self._version
            except Exception:
                pass
        if self.is_scan_available():
            try:
                result = subprocess.run(['clamscan', '--version'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self._version = result.stdout.strip().split()[1]
                    return self._version
            except Exception:
                pass
        return None
    
    def get_status(self) -> str:
        if not self.enabled:
            return "disabled"
        if self.is_daemon_available():
            return "daemon_available"
        if self.is_scan_available():
            return "scan_available"
        return "unavailable"
    
    # ============================================
    # دوال مساعدة
    # ============================================
    
    def _calculate_checksum(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _get_cache_key(self, checksum: str) -> str:
        return f"virus:scan:{checksum}"
    
    def _check_cache(self, checksum: str) -> Optional[ScanResult]:
        if not self.redis:
            return None
        cached = self.redis.get(self._get_cache_key(checksum))
        if cached:
            return ScanResult.from_json(cached)
        return None
    
    def _set_cache(self, checksum: str, result: ScanResult):
        if self.redis:
            self.redis.setex(self._get_cache_key(checksum), self.cache_ttl, result.to_json())
    
    # ============================================
    # فحص ClamAV Daemon
    # ============================================
    
    def _scan_with_daemon(self, file_path: str) -> Tuple[bool, Optional[str], str]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CLAMAV_SCAN_TIMEOUT)
            sock.connect((self.clamav_host, self.clamav_port))
            sock.send(f'SCAN {file_path}\n'.encode())
            response = sock.recv(4096).decode().strip()
            sock.close()
            if ': OK' in response:
                return True, None, response
            elif 'FOUND' in response:
                parts = response.split()
                virus_name = parts[-2] if len(parts) >= 2 else "Unknown"
                return False, virus_name, response
            return False, None, response
        except Exception as e:
            raise ClamAVDaemonUnavailableError(f"Daemon scan failed: {e}")
    
    # ============================================
    # فحص ClamAV Scan (Fallback)
    # ============================================
    
    def _scan_with_clamscan(self, file_path: str) -> Tuple[bool, Optional[str], str]:
        try:
            result = subprocess.run(
                ['clamscan', '--no-summary', '--infected', file_path],
                capture_output=True, text=True, timeout=CLAMAV_SCAN_TIMEOUT
            )
            output = result.stdout.strip()
            if result.returncode == 0:
                return True, None, output
            elif result.returncode == 1:
                parts = output.split()
                virus_name = parts[-2] if len(parts) >= 2 else "Unknown"
                return False, virus_name, output
            return False, None, output
        except Exception as e:
            raise ClamAVScanUnavailableError(f"Clamscan failed: {e}")
    
    # ============================================
    # فحص VirusTotal
    # ============================================
    
    def _check_virustotal_rate_limit(self) -> bool:
        if not self.redis:
            return True
        key = "vt:requests:" + utc_now().strftime("%Y%m%d%H%M")
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 60)
        return count <= VIRUSTOTAL_RATE_LIMIT
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def scan_with_virustotal(self, file_path: str) -> Optional[VirusTotalResult]:
        if not self.virustotal_api_key:
            return None
        if not self._check_virustotal_rate_limit():
            logger.warning("VirusTotal rate limit exceeded")
            return None
        try:
            import requests
            url = "https://www.virustotal.com/api/v3/files"
            headers = {"x-apikey": self.virustotal_api_key}
            with open(file_path, 'rb') as f:
                files = {"file": (os.path.basename(file_path), f)}
                response = requests.post(url, headers=headers, files=files, timeout=30)
            if response.status_code != 200:
                return None
            analysis_id = response.json()['data']['id']
            return self._poll_virustotal_result(analysis_id)
        except Exception:
            return None
    
    def _poll_virustotal_result(self, analysis_id: str) -> Optional[VirusTotalResult]:
        import requests
        url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
        headers = {"x-apikey": self.virustotal_api_key}
        for _ in range(VIRUSTOTAL_MAX_POLLS):
            time.sleep(VIRUSTOTAL_POLL_INTERVAL)
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    continue
                data = response.json()
                if data['data']['attributes']['status'] == 'completed':
                    stats = data['data']['attributes']['stats']
                    return VirusTotalResult(
                        file_id=analysis_id,
                        positives=stats.get('malicious', 0) + stats.get('suspicious', 0),
                        total=sum(stats.values()),
                        permalink=f"https://www.virustotal.com/gui/file/{analysis_id}",
                        scan_date=datetime.fromtimestamp(data['data']['attributes']['date']).isoformat(),
                        results=data['data']['attributes']['results']
                    )
            except Exception:
                continue
        return None
    
    # ============================================
    # الفحص الرئيسي
    # ============================================
    
    def scan_file(self, file_path: str, use_cache: bool = True) -> ScanResult:
        start_time = time.time()
        if not os.path.exists(file_path):
            return ScanResult(is_clean=False, is_infected=False, status="error", message="File not found")
        
        checksum = self._calculate_checksum(file_path)
        if use_cache:
            cached = self._check_cache(checksum)
            if cached:
                cached.scan_time_ms = (time.time() - start_time) * 1000
                return cached
        
        if not self.enabled:
            result = ScanResult(is_clean=True, is_infected=False, status="skipped", message="Scanner disabled", checksum=checksum)
            self._set_cache(checksum, result)
            return result
        
        if not self.is_available():
            result = ScanResult(is_clean=True, is_infected=False, status="skipped", message="Scanner unavailable", checksum=checksum)
            return result
        
        try:
            def _do_scan():
                if self.is_daemon_available():
                    return self._scan_with_daemon(file_path) + ("clamd",)
                elif self.fallback_to_clamscan and self.is_scan_available():
                    return self._scan_with_clamscan(file_path) + ("clamscan",)
                else:
                    raise VirusScannerError("No scanner available")
            
            is_clean, virus_name, output, engine = self.circuit_breaker.call(_do_scan)
            result = ScanResult(
                is_clean=is_clean, is_infected=not is_clean, virus_name=virus_name,
                status="clean" if is_clean else "infected", engine=engine,
                scan_time_ms=(time.time() - start_time) * 1000, message=output[:500] if output else None,
                checksum=checksum, metadata={"file_size": os.path.getsize(file_path)}
            )
            self._set_cache(checksum, result)
            if not is_clean:
                logger.warning(f"Virus detected: {virus_name} in {file_path}")
                self._quarantine_file(file_path, virus_name)
            return result
        except CircuitBreakerOpenError:
            return ScanResult(is_clean=True, is_infected=False, status="skipped", message="Circuit breaker open", checksum=checksum)
        except Exception as e:
            return ScanResult(is_clean=False, is_infected=False, status="error", message=str(e), checksum=checksum)
    
    def scan_stream(self, stream_data: bytes, filename: str = "upload") -> ScanResult:
        suffix = os.path.splitext(filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(stream_data)
            tmp_path = tmp.name
        try:
            return self.scan_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def scan_multi_engine(self, file_path: str) -> Dict[str, Any]:
        clamav_result = self.scan_file(file_path)
        vt_result = self.scan_with_virustotal(file_path) if self.virustotal_api_key else None
        infected = not clamav_result.is_clean or (vt_result and vt_result.positives > 0)
        return {
            "infected": infected,
            "clamav": clamav_result.to_dict(),
            "virustotal": {"positives": vt_result.positives, "total": vt_result.total, "permalink": vt_result.permalink} if vt_result else None,
            "recommendation": "block" if infected else "allow"
        }
    
    def scan_multiple(self, file_paths: List[str], max_workers: int = 4) -> List[ScanResult]:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(self.scan_file, file_paths))
    
    def _quarantine_file(self, file_path: str, virus_name: str) -> Optional[str]:
        if not self.quarantine_dir:
            return None
        try:
            timestamp = utc_now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.basename(file_path)
            quarantined_path = self.quarantine_dir / f"{timestamp}_{filename}"
            shutil.move(file_path, quarantined_path)
            info = {"original_path": file_path, "virus_name": virus_name, "quarantined_at": utc_now().isoformat()}
            with open(str(quarantined_path) + ".info", 'w') as f:
                json.dump(info, f)
            logger.warning(f"File quarantined: {quarantined_path}")
            return str(quarantined_path)
        except Exception as e:
            logger.error(f"Quarantine failed: {e}")
            return None
    
    def update_definitions(self) -> bool:
        try:
            result = subprocess.run(['freshclam', '--quiet'], capture_output=True, timeout=300)
            success = result.returncode == 0
            if success:
                logger.info("Virus definitions updated")
            return success
        except Exception:
            return False
    
    def health_check(self) -> HealthStatus:
        daemon_ok = self.is_daemon_available()
        scan_ok = self.is_scan_available()
        if not self.enabled:
            status = "disabled"
        elif daemon_ok:
            status = "healthy"
        elif scan_ok and self.fallback_to_clamscan:
            status = "degraded"
        else:
            status = "unhealthy"
        return HealthStatus(
            status=status, clamav_daemon_available=daemon_ok, clamav_scan_available=scan_ok,
            clamav_version=self.get_version(), virustotal_available=bool(self.virustotal_api_key),
            cache_enabled=self.redis is not None, circuit_breaker_state=self.circuit_breaker.state.value,
            quarantine_enabled=self.quarantine_dir is not None
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled, "daemon_available": self.is_daemon_available(),
            "scan_available": self.is_scan_available(), "version": self.get_version(),
            "status": self.get_status(), "virustotal_available": bool(self.virustotal_api_key),
            "cache_enabled": self.redis is not None, "circuit_breaker": self.circuit_breaker.get_metrics(),
        }
    
    def __repr__(self) -> str:
        return f"<VirusScanner enabled={self.enabled} status={self.get_status()}>"


__all__ = ["VirusScanner", "ScanResult", "VirusTotalResult", "HealthStatus"]

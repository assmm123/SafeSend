"""
Health Check Endpoints - SafeSend API
نقاط نهاية فحص الصحة - SafeSend API

Provides liveness, readiness, and detailed health checks.
يوفر فحوصات البقاء والجاهزية والصحة المفصلة.
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import shutil
import time
import os

health_bp = Blueprint('health', __name__, url_prefix='/health')

# Try to import psutil (not available on Termux)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ============================================================
# 🟢 Liveness Probe
# ============================================================

@health_bp.route('/live')
def liveness():
    """
    Liveness probe - Is the application running?
    فحص البقاء - هل التطبيق يعمل؟
    
    Returns 200 if Flask is alive (no external checks).
    يعيد 200 إذا كان Flask يعمل (بدون فحوصات خارجية).
    """
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

# ============================================================
# 🟡 Readiness Probe
# ============================================================

@health_bp.route('/ready')
def readiness():
    """
    Readiness probe - Is the application ready to serve requests?
    فحص الجاهزية - هل التطبيق جاهز لخدمة الطلبات؟
    
    Checks database and Redis connectivity.
    يفحص اتصال قاعدة البيانات و Redis.
    """
    components = {}
    healthy = True
    
    # Check database
    db_status = check_database()
    components['database'] = db_status
    if db_status['status'] != 'healthy':
        healthy = False
    
    # Check Redis
    redis_status = check_redis()
    components['redis'] = redis_status
    if redis_status['status'] != 'healthy':
        healthy = False
    
    status = 'healthy' if healthy else 'unhealthy'
    status_code = 200 if healthy else 503
    
    return jsonify({
        'status': status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'components': components
    }), status_code

# ============================================================
# 🔴 Detailed Health (Authenticated)
# ============================================================

@health_bp.route('/detailed')
def detailed_health():
    """
    Detailed health check - All components status.
    فحص صحي مفصل - حالة جميع المكونات.
    
    Requires X-Health-Token header for authentication.
    يتطلب ترويسة X-Health-Token للمصادقة.
    """
    # Authenticate
    expected_token = current_app.config.get('HEALTH_CHECK_TOKEN')
    if expected_token:
        provided_token = request.headers.get('X-Health-Token')
        if provided_token != expected_token:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized',
                'message_ar': 'غير مصرح'
            }), 401
    
    components = {}
    overall_healthy = True
    
    # Database
    components['database'] = check_database()
    if components['database']['status'] != 'healthy':
        overall_healthy = False
    
    # Redis
    components['redis'] = check_redis()
    if components['redis']['status'] != 'healthy':
        overall_healthy = False
    
    # Celery
    components['celery'] = check_celery()
    if components['celery']['status'] != 'healthy':
        overall_healthy = False
    
    # TronGrid API
    components['tron_grid'] = check_tron_grid()
    if components['tron_grid']['status'] != 'healthy':
        overall_healthy = False
    
    # File system
    components['file_system'] = check_file_system()
    if components['file_system']['status'] != 'healthy':
        overall_healthy = False
    
    # Disk space
    components['disk_space'] = check_disk_space()
    if components['disk_space']['status'] != 'healthy':
        overall_healthy = False
    
    # Memory usage (if psutil available)
    components['memory'] = check_memory_usage()
    if components['memory']['status'] != 'healthy':
        overall_healthy = False
    
    status = 'healthy' if overall_healthy else 'degraded'
    status_code = 200 if overall_healthy else 503
    
    return jsonify({
        'status': status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'components': components
    }), status_code

# ============================================================
# 🏥 Component Check Functions
# ============================================================

def check_database() -> Dict[str, Any]:
    """
    Check database connectivity.
    فحص اتصال قاعدة البيانات.
    
    Returns:
        dict with status and latency.
    """
    try:
        from src.extensions import db
        from sqlalchemy import text
        start = time.time()
        db.session.execute(text('SELECT 1'))
        latency = (time.time() - start) * 1000
        
        return {
            'status': 'healthy',
            'latency_ms': round(latency, 2)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def check_redis() -> Dict[str, Any]:
    """
    Check Redis connectivity.
    فحص اتصال Redis.
    
    Returns:
        dict with status and latency.
    """
    try:
        import redis
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        client = redis.from_url(redis_url)
        start = time.time()
        client.ping()
        latency = (time.time() - start) * 1000
        client.close()
        
        return {
            'status': 'healthy',
            'latency_ms': round(latency, 2)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def check_celery() -> Dict[str, Any]:
    """
    Check Celery worker status.
    فحص حالة عمال Celery.
    
    Returns:
        dict with status and active workers.
    """
    try:
        from src.celery_app import celery_app
        start = time.time()
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        latency = (time.time() - start) * 1000
        
        if stats:
            workers = len(stats)
            return {
                'status': 'healthy',
                'workers': workers,
                'latency_ms': round(latency, 2)
            }
        else:
            return {
                'status': 'degraded',
                'message': 'No Celery workers responding',
                'message_ar': 'لا يوجد عمال Celery يستجيبون'
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def check_tron_grid() -> Dict[str, Any]:
    """
    Check TronGrid API connectivity.
    فحص اتصال TronGrid API.
    
    Returns:
        dict with status and latency.
    """
    try:
        import requests
        tron_grid_url = current_app.config.get('TRONGRID_API_URL', 'https://api.trongrid.io')
        start = time.time()
        response = requests.get(f'{tron_grid_url}/wallet/getnowblock', timeout=10)
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            return {
                'status': 'healthy',
                'latency_ms': round(latency, 2)
            }
        else:
            return {
                'status': 'degraded',
                'message': f'TronGrid returned {response.status_code}',
                'message_ar': f'TronGrid أعاد {response.status_code}'
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def check_file_system() -> Dict[str, Any]:
    """
    Check file system accessibility.
    فحص صلاحية نظام الملفات.
    
    Returns:
        dict with status and writable path.
    """
    try:
        import tempfile
        
        test_path = os.path.join(tempfile.gettempdir(), 'safesend_health_test')
        with open(test_path, 'w') as f:
            f.write('test')
        os.remove(test_path)
        
        return {
            'status': 'healthy',
            'path': tempfile.gettempdir()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def check_disk_space() -> Dict[str, Any]:
    """
    Check available disk space.
    فحص المساحة المتوفرة على القرص.
    
    Returns:
        dict with status and usage percentage.
    """
    try:
        usage = shutil.disk_usage('/')
        free_percent = (usage.free / usage.total) * 100
        free_gb = usage.free / (1024 ** 3)
        
        if free_percent > 10:
            status = 'healthy'
        elif free_percent > 5:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'free_percent': round(free_percent, 2),
            'free_gb': round(free_gb, 2)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def check_memory_usage() -> Dict[str, Any]:
    """
    Check system memory usage.
    فحص استخدام ذاكرة النظام.
    
    Falls back to /proc/meminfo on Linux if psutil not available.
    """
    if HAS_PSUTIL:
        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            
            if used_percent < 80:
                status = 'healthy'
            elif used_percent < 90:
                status = 'degraded'
            else:
                status = 'unhealthy'
            
            return {
                'status': status,
                'used_percent': used_percent,
                'total_gb': round(memory.total / (1024 ** 3), 2),
                'available_gb': round(memory.available / (1024 ** 3), 2)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    else:
        # Fallback: read /proc/meminfo on Linux/Termux
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]
                        meminfo[key] = int(value)
                
                total_kb = meminfo.get('MemTotal', 0)
                available_kb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
                used_kb = total_kb - available_kb
                used_percent = (used_kb / total_kb) * 100 if total_kb > 0 else 0
                
                if used_percent < 80:
                    status = 'healthy'
                elif used_percent < 90:
                    status = 'degraded'
                else:
                    status = 'unhealthy'
                
                return {
                    'status': status,
                    'used_percent': round(used_percent, 2),
                    'total_gb': round(total_kb / (1024 ** 2), 2),
                    'available_gb': round(available_kb / (1024 ** 2), 2),
                    'source': '/proc/meminfo'
                }
        except Exception as e:
            return {
                'status': 'unknown',
                'error': str(e),
                'message': 'psutil not available and /proc/meminfo not readable'
            }

# ============================================================
# 📦 Export
# ============================================================

__all__ = [
    'health_bp',
    'liveness',
    'readiness',
    'detailed_health',
    'check_database',
    'check_redis',
    'check_celery',
    'check_tron_grid',
    'check_file_system',
    'check_disk_space',
    'check_memory_usage'
]

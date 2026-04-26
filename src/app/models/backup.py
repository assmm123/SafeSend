"""
نظام النسخ الاحتياطي
Backup System

يدعم:
- PostgreSQL (إنتاج حقيقي على Termux/VPS)
- SQLite (تطوير)
- نسخ احتياطي للملفات
- جدولة تلقائية
- تنظيف النسخ القديمة
"""

import gzip
import json
import os
import shutil
import subprocess
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.app.models.config import get_config
from src.app.models.helpers import (
    utc_now,
    iso_format,
    generate_id,
    ensure_directory,
    get_file_hash,
    format_file_size,
)
from src.app.models.logging_config import get_logger

logger = get_logger(__name__)


def detect_environment() -> str:
    """كشف بيئة التشغيل"""
    if os.path.exists('/data/data/com.termux'):
        return 'termux'
    import platform
    if platform.system() == 'Linux':
        try:
            subprocess.run(['systemctl', '--version'], capture_output=True)
            return 'vps'
        except:
            pass
    return 'development'


def get_database_type(db_url: str) -> str:
    """تحديد نوع قاعدة البيانات"""
    if 'postgresql' in db_url:
        return 'postgresql'
    elif 'sqlite' in db_url:
        return 'sqlite'
    return 'unknown'


def parse_postgres_url(db_url: str) -> Dict[str, str]:
    """تحليل URL PostgreSQL"""
    url = db_url.replace('postgresql://', '')
    auth, rest = url.split('@')
    user, password = auth.split(':')
    host_port, dbname = rest.split('/')
    if ':' in host_port:
        host, port = host_port.split(':')
    else:
        host, port = host_port, '5432'
    return {'user': user, 'password': password, 'host': host, 'port': port, 'dbname': dbname}


def backup_postgresql(db_url: str, backup_path: str) -> bool:
    """نسخ احتياطي لـ PostgreSQL"""
    try:
        parsed = parse_postgres_url(db_url)
        env = os.environ.copy()
        env['PGPASSWORD'] = parsed['password']
        cmd = ['pg_dump', '-h', parsed['host'], '-p', parsed['port'], '-U', parsed['user'], '-d', parsed['dbname'], '-f', backup_path, '--no-owner', '--no-privileges']
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False


def backup_sqlite(db_url: str, backup_path: str) -> bool:
    """نسخ احتياطي لـ SQLite"""
    try:
        db_path = db_url.replace('sqlite:///', '')
        with open(backup_path, 'w') as f:
            result = subprocess.run(['sqlite3', db_path, '.dump'], stdout=f, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except:
        return False


def backup_database(backup_dir: Optional[str] = None) -> Optional[str]:
    """إنشاء نسخة احتياطية لقاعدة البيانات"""
    config = get_config()
    db_url = config.SQLALCHEMY_DATABASE_URI
    if backup_dir is None:
        backup_dir = config.BACKUP_DIR
    
    db_dir = Path(backup_dir) / 'database'
    ensure_directory(db_dir)
    
    timestamp = utc_now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_dir / f"nexus_db_{timestamp}.sql"
    db_type = get_database_type(db_url)
    
    success = False
    if db_type == 'postgresql':
        success = backup_postgresql(db_url, str(backup_path))
    elif db_type == 'sqlite':
        success = backup_sqlite(db_url, str(backup_path))
    else:
        return None
    
    if success and backup_path.exists():
        compressed = str(backup_path) + '.gz'
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(backup_path)
        return compressed
    return None


def backup_files(backup_dir: Optional[str] = None) -> Optional[str]:
    """إنشاء نسخة احتياطية للملفات"""
    config = get_config()
    if backup_dir is None:
        backup_dir = config.BACKUP_DIR
    
    files_dir = Path(backup_dir) / 'files'
    ensure_directory(files_dir)
    
    storage_path = os.getenv('STORAGE_PATH', './storage')
    if not os.path.exists(storage_path):
        return None
    
    timestamp = utc_now().strftime('%Y%m%d_%H%M%S')
    backup_path = files_dir / f"nexus_files_{timestamp}.tar.gz"
    
    with tarfile.open(backup_path, 'w:gz') as tar:
        tar.add(storage_path, arcname='storage')
    return str(backup_path)


def backup_full(backup_dir: Optional[str] = None) -> Optional[str]:
    """إنشاء نسخة احتياطية كاملة"""
    config = get_config()
    if backup_dir is None:
        backup_dir = config.BACKUP_DIR
    
    full_dir = Path(backup_dir) / 'full'
    ensure_directory(full_dir)
    
    timestamp = utc_now().strftime('%Y%m%d_%H%M%S')
    backup_path = full_dir / f"nexus_full_{timestamp}.tar.gz"
    
    temp_dir = Path(backup_dir) / 'temp' / timestamp
    ensure_directory(temp_dir)
    
    try:
        db_backup = backup_database(str(temp_dir))
        if db_backup:
            shutil.copy(db_backup, temp_dir / 'database.sql.gz')
        
        storage_path = os.getenv('STORAGE_PATH', './storage')
        if os.path.exists(storage_path):
            shutil.copytree(storage_path, temp_dir / 'storage', dirs_exist_ok=True)
        
        with tarfile.open(backup_path, 'w:gz') as tar:
            tar.add(temp_dir, arcname=f'nexus_backup_{timestamp}')
        
        return str(backup_path)
    except Exception as e:
        logger.error(f"Full backup failed: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def list_backups(backup_type: str = 'all') -> List[Dict[str, Any]]:
    """عرض النسخ الاحتياطية المتاحة"""
    config = get_config()
    backup_dir = Path(config.BACKUP_DIR)
    backups = []
    types_to_search = ['database', 'files', 'full'] if backup_type == 'all' else [backup_type]
    
    for btype in types_to_search:
        type_dir = backup_dir / btype
        if type_dir.exists():
            for f in type_dir.glob('*.gz'):
                backups.append({
                    'backup_id': f.stem,
                    'type': btype,
                    'filename': f.name,
                    'path': str(f),
                    'created_at': iso_format(datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)),
                    'size_bytes': f.stat().st_size,
                })
    return sorted(backups, key=lambda x: x['created_at'], reverse=True)


def cleanup_old_backups(retention_days: int = 30) -> int:
    """حذف النسخ القديمة"""
    config = get_config()
    retention_days = retention_days or config.BACKUP_RETENTION_DAYS
    cutoff = utc_now() - timedelta(days=retention_days)
    
    deleted = 0
    for backup in list_backups():
        created = datetime.fromisoformat(backup['created_at'].replace('Z', '+00:00'))
        if created < cutoff:
            Path(backup['path']).unlink(missing_ok=True)
            deleted += 1
    return deleted


__all__ = [
    'detect_environment',
    'get_database_type',
    'backup_database',
    'backup_files',
    'backup_full',
    'list_backups',
    'cleanup_old_backups',
]

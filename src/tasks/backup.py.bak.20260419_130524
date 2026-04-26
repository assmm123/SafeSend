from datetime import datetime, timezone
"""
from datetime import datetime, timezone
from datetime import datetime, timezone
مهام النسخ الاحتياطي
Backup Tasks
"""

import os
from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='backup.database',
    max_retries=2,
    default_retry_delay=300,
    time_limit=1800,
    queue='backup'
)
def backup_database_task(self):
    """
    نسخ احتياطي لقاعدة البيانات
    Backup database
    """
    logger.info("Starting database backup")
    
    try:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_dir = os.environ.get('BACKUP_DIR', './backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = f"{backup_dir}/database_{timestamp}.sql"
        
        # SQLite backup
        db_path = os.environ.get('DATABASE_URL', 'sqlite:///nexus.db').replace('sqlite:///', '')
        if os.path.exists(db_path):
            import sqlite3
            conn = sqlite3.connect(db_path)
            with open(backup_path, 'w') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')
            conn.close()
            
            logger.info(f"Database backup complete: {backup_path}")
            return {'status': 'success', 'backup_path': backup_path}
        
        return {'status': 'skipped', 'reason': 'Database not found'}
        
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='backup.files',
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,
    queue='backup'
)
def backup_files_task(self):
    """
    نسخ احتياطي للملفات
    Backup files
    """
    logger.info("Starting files backup")
    
    try:
        import shutil
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_dir = os.environ.get('BACKUP_DIR', './backups')
        storage_path = os.environ.get('STORAGE_PATH', './storage')
        
        if os.path.exists(storage_path):
            backup_path = f"{backup_dir}/files_{timestamp}.tar.gz"
            shutil.make_archive(backup_path.replace('.tar.gz', ''), 'gztar', storage_path)
            
            logger.info(f"Files backup complete: {backup_path}")
            return {'status': 'success', 'backup_path': backup_path}
        
        return {'status': 'skipped', 'reason': 'Storage not found'}
        
    except Exception as e:
        logger.error(f"Files backup failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='backup.full',
    max_retries=2,
    default_retry_delay=600,
    time_limit=7200,
    queue='backup'
)
def backup_full_task(self):
    """
    نسخ احتياطي كامل
    Full backup
    """
    logger.info("Starting full backup")
    
    try:
        db_result = backup_database_task.delay().get()
        files_result = backup_files_task.delay().get()
        
        return {
            'status': 'success',
            'database': db_result,
            'files': files_result
        }
        
    except Exception as e:
        logger.error(f"Full backup failed: {e}")
        raise self.retry(exc=e)

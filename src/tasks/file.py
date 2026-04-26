"""
مهام الملفات
File Tasks
"""

import os
from celery import shared_task
from celery.utils.log import get_task_logger

from src.services.file_handler import FileHandler
from src.services.virus_scanner import VirusScanner

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='file.assemble_chunks',
    max_retries=3,
    default_retry_delay=60,
    queue='file'
)
def assemble_chunks_task(self, upload_id: str):
    """
    تجميع قطع الملف
    Assemble file chunks
    """
    logger.info(f"Assembling chunks: {upload_id}")
    
    try:
        handler = FileHandler()
        result = handler.assemble_chunks(upload_id)
        
        if result:
            logger.info(f"Chunks assembled: {result}")
            return {'status': 'success', 'file_path': result}
        else:
            raise Exception("Assembly failed")
            
    except Exception as e:
        logger.error(f"Assembly failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='file.virus_scan',
    max_retries=2,
    default_retry_delay=300,
    time_limit=300,
    queue='file'
)
def virus_scan_task(self, file_path: str):
    """
    فحص الفيروسات
    Virus scan
    """
    logger.info(f"Scanning file: {file_path}")
    
    try:
        scanner = VirusScanner()
        result = scanner.scan_file(file_path)
        
        return {
            'status': 'success',
            'is_clean': result.is_clean,
            'virus_name': result.virus_name
        }
        
    except Exception as e:
        logger.error(f"Virus scan failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='file.cleanup_temp_files',
    queue='file'
)
def cleanup_temp_files_task(self, max_age_hours: int = 24):
    """
    تنظيف الملفات المؤقتة
    Cleanup temporary files
    """
    logger.info(f"Cleaning up temp files older than {max_age_hours}h")
    
    try:
        handler = FileHandler()
        deleted = handler.cleanup_temp_files(max_age_hours)
        
        logger.info(f"Cleaned up {deleted} temp files")
        return {'status': 'success', 'deleted': deleted}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {'status': 'error', 'error': str(e)}

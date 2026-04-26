"""
مهام العلامات المائية
Watermark Tasks
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from src.services.watermark import WatermarkEngine
from src.app.models.helpers import utc_now

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name='watermark.process_image',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    queue='watermark'
)
def process_image_task(self, input_path: str, watermark_text: str, deal_id: str = None):
    """
    إضافة علامة مائية على صورة
    Add watermark to image
    
    Args:
        input_path: مسار الصورة
        watermark_text: نص العلامة
        deal_id: معرف الصفقة
    """
    logger.info(f"Processing image: {input_path}")
    
    try:
        engine = WatermarkEngine()
        result = engine.process_image(input_path, watermark_text)
        
        if result.success:
            logger.info(f"Image processed: {result.output_path}")
            return {'status': 'success', 'output_path': result.output_path}
        else:
            raise Exception(result.error)
            
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='watermark.process_video',
    max_retries=2,
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
    time_limit=600,
    soft_time_limit=480,
    queue='watermark'
)
def process_video_task(self, input_path: str, watermark_text: str, deal_id: str = None):
    """
    إضافة علامة مائية على فيديو
    Add watermark to video
    """
    logger.info(f"Processing video: {input_path}")
    
    try:
        engine = WatermarkEngine()
        result = engine.process_video(input_path, watermark_text)
        
        if result.success:
            logger.info(f"Video processed: {result.output_path}")
            return {'status': 'success', 'output_path': result.output_path}
        else:
            raise Exception(result.error)
            
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='watermark.process_pdf',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    queue='watermark'
)
def process_pdf_task(self, input_path: str, watermark_text: str, deal_id: str = None):
    """
    إضافة علامة مائية على PDF
    Add watermark to PDF
    """
    logger.info(f"Processing PDF: {input_path}")
    
    try:
        engine = WatermarkEngine()
        result = engine.process_pdf(input_path, watermark_text)
        
        if result.success:
            logger.info(f"PDF processed: {result.output_path}")
            return {'status': 'success', 'output_path': result.output_path}
        else:
            raise Exception(result.error)
            
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise self.retry(exc=e)

"""
اختبارات مهام Celery
Unit Tests for Celery Tasks
"""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest


class TestWatermarkTasks:
    """اختبارات مهام العلامات المائية"""
    
    @patch('src.tasks.watermark.WatermarkEngine')
    def test_process_image_task(self, mock_engine):
        from src.tasks.watermark import process_image_task
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_path = '/output/test.jpg'
        mock_engine.return_value.process_image.return_value = mock_result
        
        result = process_image_task('/input/test.jpg', 'CONFIDENTIAL')
        assert result['status'] == 'success'
        assert result['output_path'] == '/output/test.jpg'
    
    @patch('src.tasks.watermark.WatermarkEngine')
    def test_process_video_task(self, mock_engine):
        from src.tasks.watermark import process_video_task
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_path = '/output/test.mp4'
        mock_engine.return_value.process_video.return_value = mock_result
        
        result = process_video_task('/input/test.mp4', 'CONFIDENTIAL')
        assert result['status'] == 'success'
        assert result['output_path'] == '/output/test.mp4'


class TestFileTasks:
    """اختبارات مهام الملفات"""
    
    @patch('src.tasks.file.FileHandler')
    def test_assemble_chunks_task(self, mock_handler):
        from src.tasks.file import assemble_chunks_task
        
        mock_handler.return_value.assemble_chunks.return_value = '/output/assembled.dat'
        
        result = assemble_chunks_task('upload-123')
        assert result['status'] == 'success'
        assert result['file_path'] == '/output/assembled.dat'
    
    @patch('src.tasks.file.FileHandler')
    def test_cleanup_temp_files_task(self, mock_handler):
        from src.tasks.file import cleanup_temp_files_task
        
        mock_handler.return_value.cleanup_temp_files.return_value = 10
        
        result = cleanup_temp_files_task(24)
        assert result['status'] == 'success'
        assert result['deleted'] == 10


class TestPaymentTasks:
    """اختبارات مهام المدفوعات"""
    
    @patch('src.tasks.payment.TronService')
    @patch('src.tasks.payment.DealRepository')
    def test_scan_incoming_payments_task(self, mock_repo, mock_tron):
        from src.tasks.payment import scan_incoming_payments_task
        
        mock_repo.return_value.get_pending_funding.return_value = []
        
        result = scan_incoming_payments_task()
        assert result['status'] == 'success'
        assert 'processed' in result
    
    @patch('src.tasks.payment.TronService')
    @patch('src.tasks.payment.DealRepository')
    @patch('src.tasks.payment.EscrowEngine')
    def test_process_payout_task(self, mock_engine, mock_repo, mock_tron):
        from src.tasks.payment import process_payout_task
        
        mock_deal = MagicMock()
        mock_repo.return_value.get_by_id.return_value = mock_deal
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.tx_hash = 'tx-123'
        mock_engine.return_value.process_payout.return_value = mock_result
        
        result = process_payout_task('deal-123', 'idempotency-123')
        assert result['status'] == 'success'
        assert result['tx_hash'] == 'tx-123'


class TestNotificationTasks:
    """اختبارات مهام الإشعارات"""
    
    @patch('src.tasks.notification.NotificationService')
    def test_send_email_batch_task(self, mock_service):
        from src.tasks.notification import send_email_batch_task
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_service.return_value.send_email.return_value = mock_result
        
        result = send_email_batch_task(['user@test.com'], 'Subject', 'Body')
        assert result['status'] == 'success'
        assert result['sent'] == 1
    
    @patch('src.tasks.notification.NotificationService')
    def test_send_push_batch_task(self, mock_service):
        from src.tasks.notification import send_push_batch_task
        
        mock_result = MagicMock()
        mock_result.success = 5
        mock_result.total = 5
        mock_result.to_dict.return_value = {'success': 5, 'total': 5}
        mock_service.return_value.send_to_multiple.return_value = mock_result
        
        result = send_push_batch_task(['user1', 'user2'], 'Title', 'Body')
        assert result['status'] == 'success'


class TestBackupTasks:
    """اختبارات مهام النسخ الاحتياطي"""
    
    def test_backup_database_task(self):
        from src.tasks.backup import backup_database_task
        
        with patch('os.path.exists', return_value=False):
            result = backup_database_task()
            assert result['status'] == 'skipped'
    
    def test_backup_files_task(self):
        from src.tasks.backup import backup_files_task
        
        with patch('os.path.exists', return_value=False):
            result = backup_files_task()
            assert result['status'] == 'skipped'


class TestMaintenanceTasks:
    """اختبارات مهام الصيانة"""
    
    def test_cleanup_expired_sessions_task(self):
        from src.tasks.maintenance import cleanup_expired_sessions_task
        
        result = cleanup_expired_sessions_task()
        assert result['status'] == 'success'
    
    def test_update_user_ratings_task(self):
        from src.tasks.maintenance import update_user_ratings_task
        
        result = update_user_ratings_task()
        assert result['status'] == 'success'
    
    def test_check_stalled_deals_task(self):
        from src.tasks.maintenance import check_stalled_deals_task
        
        result = check_stalled_deals_task()
        assert result['status'] == 'success'


__all__ = [
    "TestWatermarkTasks",
    "TestFileTasks",
    "TestPaymentTasks",
    "TestNotificationTasks",
    "TestBackupTasks",
    "TestMaintenanceTasks",
]

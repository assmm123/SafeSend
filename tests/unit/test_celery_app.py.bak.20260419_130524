"""
اختبارات تطبيق Celery
Unit Tests for Celery Application
"""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest


class TestCeleryApp:
    """اختبارات تطبيق Celery"""
    
    @patch('src.celery_app.Celery')
    def test_create_celery(self, mock_celery):
        """اختبار إنشاء تطبيق Celery"""
        from src.celery_app import create_celery
        
        mock_instance = MagicMock()
        mock_celery.return_value = mock_instance
        
        celery = create_celery('test_app')
        
        assert celery is not None
        mock_celery.assert_called_once()
    
    def test_get_redis_url_default(self):
        """اختبار عنوان Redis الافتراضي"""
        from src.celery_app import get_redis_url
        
        with patch.dict(os.environ, {}, clear=True):
            url = get_redis_url()
            assert url == 'redis://localhost:6379/0'
    
    def test_get_redis_url_from_env(self):
        """اختبار عنوان Redis من البيئة"""
        from src.celery_app import get_redis_url
        
        with patch.dict(os.environ, {'REDIS_URL': 'redis://custom:6380/1'}):
            url = get_redis_url()
            assert url == 'redis://custom:6380/1'
    
    def test_is_termux_true(self):
        """اختبار اكتشاف Termux"""
        from src.celery_app import is_termux
        
        with patch.dict(os.environ, {'TERMUX_VERSION': '1.0'}):
            assert is_termux() is True
    
    def test_is_termux_false(self):
        """اختبار عدم وجود Termux"""
        from src.celery_app import is_termux
        
        with patch.dict(os.environ, {}, clear=True):
            assert is_termux() is False


class TestCeleryHelpers:
    """اختبارات الدوال المساعدة"""
    
    @patch('src.celery_app.celery_app')
    def test_revoke_task(self, mock_app):
        """اختبار إلغاء مهمة"""
        from src.celery_app import revoke_task
        
        result = revoke_task('task-123')
        assert result is True
        mock_app.control.revoke.assert_called_once_with('task-123', terminate=False)
    
    @patch('src.celery_app.celery_app')
    def test_revoke_task_terminate(self, mock_app):
        """اختبار إلغاء مهمة مع إنهاء"""
        from src.celery_app import revoke_task
        
        result = revoke_task('task-123', terminate=True)
        assert result is True
        mock_app.control.revoke.assert_called_once_with('task-123', terminate=True)
    
    @patch('src.celery_app.celery_app')
    def test_purge_queue_all(self, mock_app):
        """اختبار تفريغ جميع القوائم"""
        from src.celery_app import purge_queue
        
        purge_queue()
        mock_app.control.purge.assert_called_once()
    
    @patch('src.celery_app.celery_app')
    def test_purge_queue_specific(self, mock_app):
        """اختبار تفريغ قائمة محددة"""
        from src.celery_app import purge_queue
        
        purge_queue('watermark')
        mock_app.control.purge.assert_called_once_with(queue='watermark')
    
    @patch('src.celery_app.celery_app')
    def test_ping_workers_no_inspect(self, mock_app):
        """اختبار ping workers بدون inspect"""
        from src.celery_app import ping_workers
        
        mock_app.control.inspect.return_value = None
        
        result = ping_workers()
        assert result == {}
    
    @patch('src.celery_app.celery_app')
    def test_ping_workers_with_response(self, mock_app):
        """اختبار ping workers مع استجابة"""
        from src.celery_app import ping_workers
        
        mock_inspect = MagicMock()
        mock_inspect.ping.return_value = {'worker1': {'ok': 'pong'}}
        mock_app.control.inspect.return_value = mock_inspect
        
        result = ping_workers()
        assert 'worker1' in result


class TestCelerySignals:
    """اختبارات Signals"""
    
    def test_task_prerun_handler(self):
        """اختبار معالج task_prerun"""
        from src.celery_app import task_prerun_handler
        
        # يجب أن يعمل بدون أخطاء
        task_prerun_handler(sender=MagicMock(), task_id='123', task=MagicMock(name='test_task'))
    
    def test_task_postrun_handler(self):
        """اختبار معالج task_postrun"""
        from src.celery_app import task_postrun_handler
        
        task_postrun_handler(
            sender=MagicMock(), task_id='123', 
            task=MagicMock(name='test_task'), retval='result', state='SUCCESS'
        )
    
    def test_task_failure_handler(self):
        """اختبار معالج task_failure"""
        from src.celery_app import task_failure_handler
        
        task_failure_handler(
            sender=MagicMock(name='test_task'), task_id='123', 
            exception=ValueError('test error')
        )
    
    def test_worker_ready_handler(self):
        """اختبار معالج worker_ready"""
        from src.celery_app import worker_ready_handler
        
        worker_ready_handler(sender=MagicMock(hostname='worker1'))
    
    def test_worker_shutdown_handler(self):
        """اختبار معالج worker_shutdown"""
        from src.celery_app import worker_shutdown_handler
        
        worker_shutdown_handler(sender=MagicMock(hostname='worker1'))


class TestCeleryFlaskIntegration:
    """اختبارات تكامل Flask"""
    
    def test_init_celery(self):
        """اختبار تهيئة Celery مع Flask"""
        from src.celery_app import init_celery
        
        mock_app = MagicMock()
        mock_app.import_name = 'test_app'
        mock_app.config = {}
        
        with patch('src.celery_app.create_celery') as mock_create:
            mock_celery = MagicMock()
            mock_create.return_value = mock_celery
            
            result = init_celery(mock_app)
            
            assert result is not None
            mock_create.assert_called_once_with('test_app')


__all__ = [
    "TestCeleryApp",
    "TestCeleryHelpers",
    "TestCelerySignals",
    "TestCeleryFlaskIntegration",
]

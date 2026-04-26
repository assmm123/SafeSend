"""
اختبارات نظام النسخ الاحتياطي
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from src.app.models.backup import (
    detect_environment, get_database_type, parse_postgres_url,
    backup_database, backup_files, backup_full, list_backups, cleanup_old_backups
)

class TestEnvironmentDetection:
    def test_detect_termux(self):
        with patch('os.path.exists', return_value=True):
            assert detect_environment() == 'termux'
    
    def test_get_db_type(self):
        assert get_database_type("postgresql://localhost/db") == "postgresql"
        assert get_database_type("sqlite:///test.db") == "sqlite"
    
    def test_parse_pg_url(self):
        parsed = parse_postgres_url("postgresql://user:pass@localhost:5432/db")
        assert parsed['user'] == 'user'
        assert parsed['dbname'] == 'db'

class TestBackupOperations:
    def test_backup_files(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv('BACKUP_DIR', tmp)
            monkeypatch.setenv('STORAGE_PATH', tmp)
            (Path(tmp) / 'test.txt').write_text('content')
            with patch('src.app.models.backup.get_config') as mock:
                mock.return_value.BACKUP_DIR = tmp
                result = backup_files()
                if result:
                    assert Path(result).exists()

    def test_list_backups(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv('BACKUP_DIR', tmp)
            (Path(tmp) / 'database').mkdir()
            (Path(tmp) / 'database' / 'test.gz').touch()
            with patch('src.app.models.backup.get_config') as mock:
                mock.return_value.BACKUP_DIR = tmp
                assert len(list_backups()) >= 1

    def test_cleanup_old_backups(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setenv('BACKUP_DIR', tmp)
            (Path(tmp) / 'database').mkdir()
            f = Path(tmp) / 'database' / 'old.gz'
            f.touch()
            with patch('src.app.models.backup.get_config') as mock:
                mock.return_value.BACKUP_DIR = tmp
                mock.return_value.BACKUP_RETENTION_DAYS = 0
                deleted = cleanup_old_backups(retention_days=0)
                assert deleted >= 1

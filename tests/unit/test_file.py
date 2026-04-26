"""
اختبارات نموذج الملفات
Unit Tests for File Model
"""

import sys
import os
import tempfile
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models.base import Base
from src.app.models.user import User
from src.app.models.file import File, FileType, VirusScanResult, FileStatus
from src.app.models.helpers import utc_now


@pytest.fixture
def db_session():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()


@pytest.fixture
def test_user(db_session):
    user = User(email="file_test@ex.com", username="fileuser")
    user.set_password("Test123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_file(db_session, test_user):
    file = File(
        uploader_id=str(test_user.id),
        original_name="test.pdf",
        stored_name="abc_test.pdf",
        file_path="/uploads/abc_test.pdf",
        file_size=1024000,
        mime_type="application/pdf",
        extension=".pdf",
        checksum="sha256_abc"
    )
    db_session.add(file)
    db_session.commit()
    return file


class TestFileBasic:
    def test_create_file(self, db_session, test_user):
        file = File(
            uploader_id=str(test_user.id),
            original_name="doc.pdf",
            stored_name="xyz_doc.pdf",
            file_path="/uploads/xyz_doc.pdf",
            file_size=2048000,
            mime_type="application/pdf",
            extension=".pdf",
            checksum="sha256_xyz"
        )
        db_session.add(file)
        db_session.commit()
        
        assert file.id is not None
        assert file.original_name == "doc.pdf"
        assert file.status == FileStatus.UPLOADING


class TestFileProperties:
    def test_is_deleted(self, test_file):
        assert test_file.is_deleted is False
        test_file.soft_delete()
        assert test_file.is_deleted is True
    
    def test_is_expired(self, test_file):
        assert test_file.is_expired is False
        test_file.expires_at = utc_now() - timedelta(days=1)
        assert test_file.is_expired is True
    
    def test_is_virus_clean(self, test_file):
        test_file.virus_scan_result = VirusScanResult.CLEAN
        assert test_file.is_virus_clean is True
    
    def test_file_type(self, test_file):
        test_file.mime_type = "image/jpeg"
        assert test_file.file_type == FileType.IMAGE


class TestFileMethods:
    def test_mark_ready(self, test_file):
        test_file.mark_ready()
        assert test_file.status == FileStatus.READY
    
    def test_increment_download(self, test_file, test_user):
        test_file.increment_download(str(test_user.id))
        assert test_file.download_count == 1
    
    def test_soft_delete(self, test_file):
        test_file.soft_delete(reason="test")
        assert test_file.is_deleted is True
        assert test_file.status == FileStatus.DELETED
    
    def test_restore(self, test_file):
        test_file.soft_delete()
        test_file.restore()
        assert test_file.is_deleted is False
    
    def test_mark_virus_scanned(self, test_file):
        test_file.mark_virus_scanned(VirusScanResult.CLEAN)
        assert test_file.virus_scanned is True
    
    def test_set_encrypted(self, test_file):
        test_file.set_encrypted("/enc/file.enc", "checksum")
        assert test_file.encrypted is True
    
    def test_set_watermarked(self, test_file):
        test_file.set_watermarked("/wm/file.pdf", "CONFIDENTIAL")
        assert test_file.watermarked is True
    
    def test_to_dict(self, test_file):
        data = test_file.to_dict()
        assert data['id'] == str(test_file.id)
        assert data['original_name'] == "test.pdf"


__all__ = ["TestFileBasic", "TestFileProperties", "TestFileMethods"]

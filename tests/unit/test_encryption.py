"""
اختبارات خدمة التشفير
Unit Tests for Encryption Service
"""

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.services.encryption import (
    EncryptionService,
    EncryptedData,
    EncryptionAlgorithm,
    EncryptionError,
    DecryptionError,
)


@pytest.fixture
def encryption_service():
    return EncryptionService()


class TestKeyGeneration:
    def test_generate_key(self):
        key = EncryptionService.generate_key()
        assert len(key) == 32
        assert key != EncryptionService.generate_key()
    
    def test_generate_iv(self):
        iv = EncryptionService.generate_iv()
        assert len(iv) == 12
        assert iv != EncryptionService.generate_iv()
    
    def test_rotate_key(self, encryption_service):
        old_key = encryption_service._master_key
        new_key = encryption_service.rotate_key()
        assert old_key != encryption_service._master_key
        assert new_key == old_key


class TestDataEncryption:
    def test_encrypt_decrypt_bytes(self, encryption_service):
        original = b"Hello, World!"
        encrypted = encryption_service.encrypt_data(original)
        decrypted = encryption_service.decrypt_data(encrypted)
        assert decrypted == original
    
    def test_encrypt_decrypt_with_context(self, encryption_service):
        original = b"context test"
        encrypted = encryption_service.encrypt_data(original, context="test")
        decrypted = encryption_service.decrypt_data(encrypted)
        assert decrypted == original
    
    def test_encrypt_decrypt_with_compression(self, encryption_service):
        original = b"A" * 10000
        encrypted = encryption_service.encrypt_data(original, compress=True)
        decrypted = encryption_service.decrypt_data(encrypted)
        assert decrypted == original
        assert encrypted.compressed is True
    
    def test_encrypt_decrypt_with_associated_data(self, encryption_service):
        original = b"Sensitive"
        ad = b"user:123"
        encrypted = encryption_service.encrypt_data(original, associated_data=ad)
        decrypted = encryption_service.decrypt_data(encrypted, associated_data=ad)
        assert decrypted == original
    
    def test_encrypted_data_serialization(self, encryption_service):
        original = b"serialize"
        encrypted = encryption_service.encrypt_data(original)
        json_str = encrypted.to_json()
        restored = EncryptedData.from_dict(json.loads(json_str))
        decrypted = encryption_service.decrypt_data(restored)
        assert decrypted == original


class TestStringEncryption:
    def test_encrypt_decrypt_string(self, encryption_service):
        original = "Hello, عالم!"
        encrypted = encryption_service.encrypt_string(original)
        decrypted = encryption_service.decrypt_string(encrypted)
        assert decrypted == original
    
    def test_encrypt_decrypt_email(self, encryption_service):
        email = "Test@Example.COM"
        encrypted = encryption_service.encrypt_email(email)
        decrypted = encryption_service.decrypt_email(encrypted)
        assert decrypted == "test@example.com"
    
    def test_encrypt_decrypt_phone(self, encryption_service):
        phone = "+966 50 123 4567"
        encrypted = encryption_service.encrypt_phone(phone)
        decrypted = encryption_service.decrypt_phone(encrypted)
        assert decrypted == phone
    
    def test_encrypt_decrypt_json(self, encryption_service):
        data = {"user": "john", "role": "admin"}
        encrypted = encryption_service.encrypt_json(data)
        decrypted = encryption_service.decrypt_json(encrypted)
        assert decrypted == data


class TestFileEncryption:
    def test_encrypt_decrypt_file(self, encryption_service):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, World! " * 100)
            original_path = f.name
        
        encrypted_path = original_path + ".enc"
        decrypted_path = original_path + ".dec"
        
        try:
            encryption_service.encrypt_file(original_path, encrypted_path)
            encryption_service.decrypt_file(encrypted_path, decrypted_path)
            
            with open(original_path, 'rb') as f1, open(decrypted_path, 'rb') as f2:
                assert f1.read() == f2.read()
        finally:
            for p in [original_path, encrypted_path, decrypted_path]:
                if os.path.exists(p):
                    os.remove(p)


class TestHMAC:
    def test_calculate_hmac(self, encryption_service):
        data = b"important"
        sig = encryption_service.calculate_hmac(data)
        assert len(sig) == 64
    
    def test_verify_hmac_valid(self, encryption_service):
        data = b"verify"
        sig = encryption_service.calculate_hmac(data)
        assert encryption_service.verify_hmac(data, sig) is True
    
    def test_verify_hmac_invalid(self, encryption_service):
        data = b"verify"
        assert encryption_service.verify_hmac(data, "invalid") is False


class TestHealthCheck:
    def test_health_check(self, encryption_service):
        health = encryption_service.health_check()
        assert health["status"] == "healthy"
        assert health["algorithm"] == EncryptionAlgorithm.AES_256_GCM


class TestEdgeCases:
    def test_encrypt_empty_data(self, encryption_service):
        original = b""
        encrypted = encryption_service.encrypt_data(original)
        decrypted = encryption_service.decrypt_data(encrypted)
        assert decrypted == original
    
    def test_encrypt_unicode_string(self, encryption_service):
        original = "مرحبا بالعالم! 🌍"
        encrypted = encryption_service.encrypt_string(original)
        decrypted = encryption_service.decrypt_string(encrypted)
        assert decrypted == original
    
    def test_wrong_key_fails_decryption(self):
        s1 = EncryptionService()
        s2 = EncryptionService()
        encrypted = s1.encrypt_string("secret")
        with pytest.raises(DecryptionError):
            s2.decrypt_string(encrypted)

"""
اختبارات خدمات الأمان والتشفير
Unit Tests for Security and Encryption Services
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import pytest

from src.app.models.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    generate_token,
    generate_refresh_token,
    verify_token,
    decode_token,
    get_token_remaining_time,
    generate_secure_token,
    generate_secure_uuid,
    generate_api_key,
    encrypt_data,
    decrypt_data,
    hash_sha256,
    hmac_sha256,
    constant_time_compare,
    mask_email,
    mask_phone,
)


class TestPasswordHashing:
    """اختبارات تشفير كلمات المرور"""
    
    def test_hash_password_returns_string(self):
        """اختبار أن تشفير كلمة المرور يعيد نصاً"""
        hashed = hash_password("my_password")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")
    
    def test_hash_password_different_each_time(self):
        """اختبار أن التشفير مختلف في كل مرة (salt مختلف)"""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert hash1 != hash2
    
    def test_hash_password_empty_raises_error(self):
        """اختبار أن كلمة المرور الفارغة تثير خطأ"""
        with pytest.raises(ValueError):
            hash_password("")
    
    def test_verify_password_correct(self):
        """اختبار التحقق من كلمة مرور صحيحة"""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """اختبار التحقق من كلمة مرور خاطئة"""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False
    
    def test_verify_password_empty_inputs(self):
        """اختبار التحقق مع مدخلات فارغة"""
        assert verify_password("", "something") is False
        assert verify_password("something", "") is False
        assert verify_password("", "") is False


class TestPasswordStrength:
    """اختبارات قوة كلمة المرور"""
    
    def test_strong_password(self):
        """اختبار كلمة مرور قوية"""
        is_strong, message = validate_password_strength("StrongPass123!")
        assert is_strong is True
    
    def test_weak_password_short(self):
        """اختبار كلمة مرور قصيرة"""
        is_strong, message = validate_password_strength("Short1")
        assert is_strong is False
        assert "8 characters" in message
    
    def test_weak_password_no_uppercase(self):
        """اختبار كلمة مرور بدون حرف كبير"""
        is_strong, message = validate_password_strength("lowercase123")
        assert is_strong is False
        assert "uppercase" in message
    
    def test_weak_password_no_lowercase(self):
        """اختبار كلمة مرور بدون حرف صغير"""
        is_strong, message = validate_password_strength("UPPERCASE123")
        assert is_strong is False
        assert "lowercase" in message
    
    def test_weak_password_no_number(self):
        """اختبار كلمة مرور بدون رقم"""
        is_strong, message = validate_password_strength("NoNumberPass")
        assert is_strong is False
        assert "number" in message


class TestJWTToken:
    """اختبارات توكنات JWT"""
    
    def test_generate_token_returns_string(self):
        """اختبار أن توليد التوكن يعيد نصاً"""
        token = generate_token({"user_id": "123"})
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_token_with_expiry(self):
        """اختبار توليد توكن مع مدة صلاحية"""
        token = generate_token({"user_id": "123"}, expires_in=60)
        assert isinstance(token, str)
    
    def test_generate_refresh_token(self):
        """اختبار توليد توكن تحديث"""
        token = generate_refresh_token("user_123")
        assert isinstance(token, str)
        payload = verify_token(token, token_type="refresh")
        assert payload is not None
        assert payload["user_id"] == "user_123"
        assert payload["type"] == "refresh"
    
    def test_verify_valid_token(self):
        """اختبار التحقق من توكن صالح"""
        token = generate_token({"user_id": "456", "role": "admin"})
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "456"
        assert payload["role"] == "admin"
    
    def test_verify_token_with_type(self):
        """اختبار التحقق من نوع التوكن"""
        token = generate_token({"user_id": "123"}, token_type="access")
        payload = verify_token(token, token_type="access")
        assert payload is not None
        
        payload = verify_token(token, token_type="refresh")
        assert payload is None
    
    def test_verify_expired_token(self):
        """اختبار التحقق من توكن منتهي الصلاحية"""
        token = generate_token({"user_id": "123"}, expires_in=-1)
        time.sleep(1)
        payload = verify_token(token)
        assert payload is None
    
    def test_verify_invalid_token(self):
        """اختبار التحقق من توكن غير صالح"""
        payload = verify_token("invalid.token.here")
        assert payload is None
    
    def test_decode_token(self):
        """اختبار فك تشفير التوكن"""
        token = generate_token({"user_id": "789"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == "789"
    
    def test_get_token_remaining_time(self):
        """اختبار الحصول على الوقت المتبقي للتوكن"""
        token = generate_token({"user_id": "123"}, expires_in=3600)
        remaining = get_token_remaining_time(token)
        assert remaining is not None
        assert remaining > 3500
        assert remaining <= 3600
    
    def test_get_token_remaining_time_invalid(self):
        """اختبار الوقت المتبقي لتوكن غير صالح"""
        remaining = get_token_remaining_time("invalid")
        assert remaining is None


class TestSecureRandom:
    """اختبارات التوليد العشوائي الآمن"""
    
    def test_generate_secure_token_default_length(self):
        """اختبار توليد توكن آمن بالطول الافتراضي"""
        token = generate_secure_token()
        assert isinstance(token, str)
        assert len(token) == 32
    
    def test_generate_secure_token_custom_length(self):
        """اختبار توليد توكن آمن بطول مخصص"""
        token = generate_secure_token(64)
        assert len(token) == 64
    
    def test_generate_secure_token_unique(self):
        """اختبار أن التوكنات فريدة"""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        assert token1 != token2
    
    def test_generate_secure_uuid(self):
        """اختبار توليد UUID آمن"""
        uuid_val = generate_secure_uuid()
        assert isinstance(uuid_val, str)
        assert len(uuid_val) == 36
        assert uuid_val.count('-') == 4
    
    def test_generate_api_key(self):
        """اختبار توليد مفتاح API"""
        api_key = generate_api_key()
        assert api_key.startswith("nexus_")
        assert len(api_key) >= len("nexus_") + 30
    
    def test_generate_api_key_custom_prefix(self):
        """اختبار توليد مفتاح API ببادئة مخصصة"""
        api_key = generate_api_key(prefix="test")
        assert api_key.startswith("test_")


class TestDataEncryption:
    """اختبارات تشفير البيانات"""
    
    def test_encrypt_decrypt_roundtrip(self):
        """اختبار تشفير وفك تشفير البيانات"""
        original = "sensitive data here"
        encrypted = encrypt_data(original)
        assert encrypted != original
        decrypted = decrypt_data(encrypted)
        assert decrypted == original
    
    def test_encrypt_empty_string(self):
        """اختبار تشفير نص فارغ"""
        encrypted = encrypt_data("")
        assert encrypted == ""
        decrypted = decrypt_data("")
        assert decrypted == ""
    
    def test_decrypt_invalid_data(self):
        """اختبار فك تشفير بيانات غير صالحة"""
        with pytest.raises(ValueError):
            decrypt_data("invalid_encrypted_data")
    
    def test_encrypt_different_each_time(self):
        """اختبار أن التشفير مختلف في كل مرة (IV مختلف)"""
        data = "same data"
        enc1 = encrypt_data(data)
        enc2 = encrypt_data(data)
        assert enc1 != enc2


class TestHashing:
    """اختبارات التجزئة"""
    
    def test_hash_sha256(self):
        """اختبار تجزئة SHA256"""
        hash1 = hash_sha256("hello world")
        hash2 = hash_sha256("hello world")
        assert hash1 == hash2
        assert len(hash1) == 64
    
    def test_hmac_sha256(self):
        """اختبار HMAC SHA256"""
        key = "secret_key"
        message = "important message"
        hmac1 = hmac_sha256(key, message)
        hmac2 = hmac_sha256(key, message)
        assert hmac1 == hmac2
        assert len(hmac1) == 64
        
        hmac_wrong_key = hmac_sha256("wrong_key", message)
        assert hmac1 != hmac_wrong_key


class TestHelperFunctions:
    """اختبارات الدوال المساعدة"""
    
    def test_constant_time_compare_equal(self):
        """اختبار المقارنة الآمنة للقيم المتطابقة"""
        assert constant_time_compare("abc123", "abc123") is True
    
    def test_constant_time_compare_not_equal(self):
        """اختبار المقارنة الآمنة للقيم المختلفة"""
        assert constant_time_compare("abc123", "xyz789") is False
    
    def test_constant_time_compare_different_lengths(self):
        """اختبار المقارنة الآمنة لأطوال مختلفة"""
        assert constant_time_compare("abc", "abcdef") is False
    
    def test_mask_email(self):
        """اختبار إخفاء البريد الإلكتروني"""
        masked = mask_email("user@example.com")
        assert masked == "u***r@example.com"
        
        masked_short = mask_email("a@example.com")
        assert masked_short == "a***@example.com"
    
    def test_mask_email_no_at_symbol(self):
        """اختبار إخفاء بريد بدون @"""
        masked = mask_email("invalid_email")
        assert masked == "invalid_email"
    
    def test_mask_phone(self):
        """اختبار إخفاء رقم الهاتف"""
        masked = mask_phone("+966501234567")
        assert masked == "+96650****567"
    
    def test_mask_phone_short(self):
        """اختبار إخفاء رقم هاتف قصير"""
        masked = mask_phone("12345")
        assert masked == "*****"


class TestSecurityIntegration:
    """اختبارات تكاملية للأمان"""
    
    def test_full_auth_flow(self):
        """اختبار تدفق المصادقة الكامل"""
        # 1. المستخدم يسجل بكلمة مرور
        password = "SecurePass123!"
        hashed = hash_password(password)
        
        # 2. التحقق من كلمة المرور
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPass", hashed) is False
        
        # 3. توليد توكن
        token = generate_token({"user_id": "user_123", "role": "user"})
        assert token is not None
        
        # 4. التحقق من التوكن
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "user_123"
        
        # 5. توليد refresh token
        refresh = generate_refresh_token("user_123")
        refresh_payload = verify_token(refresh, token_type="refresh")
        assert refresh_payload is not None
    
    def test_encrypted_data_storage_flow(self):
        """اختبار تدفق تخزين البيانات المشفرة"""
        sensitive_data = "API_KEY_12345_SECRET"
        encrypted = encrypt_data(sensitive_data)
        decrypted = decrypt_data(encrypted)
        assert decrypted == sensitive_data


__all__ = [
    "TestPasswordHashing",
    "TestPasswordStrength",
    "TestJWTToken",
    "TestSecureRandom",
    "TestDataEncryption",
    "TestHashing",
    "TestHelperFunctions",
    "TestSecurityIntegration",
]

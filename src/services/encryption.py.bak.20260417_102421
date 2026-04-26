"""
خدمة التشفير المتقدمة
Advanced Encryption Service

AES-256-GCM مع دعم اشتقاق المفاتيح للسياقات
"""

import base64
import hashlib
import hmac
import json
import os
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from src.app.models.helpers import generate_id
from src.app.models.logging_config import get_logger

logger = get_logger(__name__)


# ============================================
# الثوابت
# ============================================

class EncryptionAlgorithm:
    AES_256_GCM = "AES-256-GCM"

KEY_SIZE = 32
IV_SIZE = 12
TAG_SIZE = 16
SALT_SIZE = 16
CHUNK_SIZE = 1024 * 1024


# ============================================
# Data Classes
# ============================================

@dataclass
class EncryptedData:
    ciphertext: str
    iv: str
    tag: str
    algorithm: str = EncryptionAlgorithm.AES_256_GCM
    compressed: bool = False
    context: Optional[str] = None
    salt: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = {
            "ciphertext": self.ciphertext,
            "iv": self.iv,
            "tag": self.tag,
            "algorithm": self.algorithm,
            "compressed": self.compressed,
        }
        if self.context:
            result["context"] = self.context
        if self.salt:
            result["salt"] = self.salt
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EncryptedData':
        return cls(
            ciphertext=data["ciphertext"],
            iv=data["iv"],
            tag=data["tag"],
            algorithm=data.get("algorithm", EncryptionAlgorithm.AES_256_GCM),
            compressed=data.get("compressed", False),
            context=data.get("context"),
            salt=data.get("salt"),
        )


# ============================================
# Exceptions
# ============================================

class EncryptionError(Exception):
    pass

class DecryptionError(Exception):
    pass


# ============================================
# Encryption Service
# ============================================

class EncryptionService:
    """خدمة التشفير AES-256-GCM مع دعم السياقات"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        self._master_key = master_key or self.generate_key()
        logger.info("EncryptionService initialized")
    
    @staticmethod
    def generate_key() -> bytes:
        return os.urandom(KEY_SIZE)
    
    @staticmethod
    def generate_iv() -> bytes:
        return os.urandom(IV_SIZE)
    
    @staticmethod
    def generate_salt() -> bytes:
        return os.urandom(SALT_SIZE)
    
    def _derive_key(self, context: str, salt: bytes) -> bytes:
        """اشتقاق مفتاح من السياق والـ salt"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            info=context.encode(),
            backend=default_backend()
        )
        return hkdf.derive(self._master_key)
    
    def encrypt_data(
        self,
        data: bytes,
        associated_data: Optional[bytes] = None,
        compress: bool = False,
        context: Optional[str] = None
    ) -> EncryptedData:
        """تشفير البيانات"""
        try:
            if compress:
                data = zlib.compress(data, level=9)
            
            salt = None
            if context:
                salt = self.generate_salt()
                key = self._derive_key(context, salt)
            else:
                key = self._master_key
            
            iv = self.generate_iv()
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            if associated_data:
                encryptor.authenticate_additional_data(associated_data)
            
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            return EncryptedData(
                ciphertext=base64.b64encode(ciphertext).decode(),
                iv=base64.b64encode(iv).decode(),
                tag=base64.b64encode(encryptor.tag).decode(),
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                compressed=compress,
                context=context,
                salt=base64.b64encode(salt).decode() if salt else None,
            )
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt_data(
        self,
        encrypted: Union[EncryptedData, Dict, str],
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """فك تشفير البيانات"""
        try:
            if isinstance(encrypted, str):
                encrypted = EncryptedData.from_dict(json.loads(encrypted))
            elif isinstance(encrypted, dict):
                encrypted = EncryptedData.from_dict(encrypted)
            
            # اختيار المفتاح
            if encrypted.context and encrypted.salt:
                salt = base64.b64decode(encrypted.salt)
                key = self._derive_key(encrypted.context, salt)
            else:
                key = self._master_key
            
            iv = base64.b64decode(encrypted.iv)
            tag = base64.b64decode(encrypted.tag)
            ciphertext = base64.b64decode(encrypted.ciphertext)
            
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            
            if associated_data:
                decryptor.authenticate_additional_data(associated_data)
            
            data = decryptor.update(ciphertext) + decryptor.finalize()
            
            if encrypted.compressed:
                data = zlib.decompress(data)
            
            return data
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Decryption failed: {e}")
    
    def encrypt_string(self, text: str, context: Optional[str] = None) -> str:
        encrypted = self.encrypt_data(text.encode(), context=context)
        return encrypted.to_json()
    
    def decrypt_string(self, encrypted: str) -> str:
        return self.decrypt_data(encrypted).decode()
    
    def encrypt_email(self, email: str) -> str:
        return self.encrypt_string(email.lower().strip(), context="email")
    
    def decrypt_email(self, encrypted: str) -> str:
        return self.decrypt_string(encrypted)
    
    def encrypt_phone(self, phone: str) -> str:
        return self.encrypt_string(phone.strip(), context="phone")
    
    def decrypt_phone(self, encrypted: str) -> str:
        return self.decrypt_string(encrypted)
    
    def encrypt_json(self, data: Dict) -> str:
        return self.encrypt_string(json.dumps(data, ensure_ascii=False), context="json")
    
    def decrypt_json(self, encrypted: str) -> Dict:
        return json.loads(self.decrypt_string(encrypted))
    
    def calculate_hmac(self, data: bytes) -> str:
        return hmac.new(self._master_key, data, hashlib.sha256).hexdigest()
    
    def verify_hmac(self, data: bytes, signature: str) -> bool:
        expected = self.calculate_hmac(data)
        return hmac.compare_digest(expected, signature)
    
    def encrypt_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        if output_path is None:
            output_path = input_path + ".enc"
        
        iv = self.generate_iv()
        cipher = Cipher(algorithms.AES(self._master_key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
            fout.write(iv)
            while chunk := fin.read(CHUNK_SIZE):
                fout.write(encryptor.update(chunk))
            fout.write(encryptor.finalize())
            fout.write(encryptor.tag)
        
        return output_path
    
    def decrypt_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        if output_path is None:
            output_path = input_path.replace('.enc', '')
        
        with open(input_path, 'rb') as fin:
            iv = fin.read(IV_SIZE)
            file_data = fin.read()
            ciphertext = file_data[:-TAG_SIZE]
            tag = file_data[-TAG_SIZE:]
        
        cipher = Cipher(algorithms.AES(self._master_key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        data = decryptor.update(ciphertext) + decryptor.finalize()
        
        with open(output_path, 'wb') as fout:
            fout.write(data)
        
        return output_path
    
    def health_check(self) -> dict:
        test_data = b"health_check"
        try:
            encrypted = self.encrypt_data(test_data)
            decrypted = self.decrypt_data(encrypted)
            healthy = (test_data == decrypted)
        except:
            healthy = False
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "algorithm": EncryptionAlgorithm.AES_256_GCM,
        }
    
    def rotate_key(self) -> bytes:
        """تدوير المفتاح الرئيسي"""
        old_key = self._master_key
        self._master_key = self.generate_key()
        logger.info("Master key rotated")
        return old_key


__all__ = [
    "EncryptionService",
    "EncryptedData",
    "EncryptionAlgorithm",
    "EncryptionError",
    "DecryptionError",
]

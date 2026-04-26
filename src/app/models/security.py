"""
خدمات الأمان والتشفير
Security and Encryption Services
"""

import hashlib
import hmac
import os
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt
from cryptography.fernet import Fernet

from src.app.models.config import get_config


def _get_jwt_secret() -> str:
    config = get_config()
    return config.JWT_SECRET_KEY


def _get_bcrypt_rounds() -> int:
    config = get_config()
    return config.BCRYPT_ROUNDS


def _get_fernet() -> Fernet:
    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        fernet_key = Fernet.generate_key().decode()
        os.environ["FERNET_KEY"] = fernet_key
    return Fernet(fernet_key.encode())


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=_get_bcrypt_rounds())
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"


def generate_token(payload: Dict[str, Any], expires_in: int = 3600, token_type: str = "access") -> str:
    now = datetime.now(timezone.utc)
    token_payload = {
        **payload,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
        "nbf": now,
        "type": token_type,
    }
    return jwt.encode(token_payload, _get_jwt_secret(), algorithm="HS256")


def generate_refresh_token(user_id: str, expires_in: int = 2592000) -> str:
    return generate_token(payload={"user_id": user_id}, expires_in=expires_in, token_type="refresh")


def verify_token(token: str, token_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
        if token_type and payload.get("type") != token_type:
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None


def get_token_remaining_time(token: str) -> Optional[int]:
    payload = verify_token(token)
    if not payload:
        return None
    exp = payload.get("exp")
    if not exp:
        return None
    now = datetime.now(timezone.utc).timestamp()
    return max(0, int(exp - now))


def generate_secure_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secure_uuid() -> str:
    import uuid
    return str(uuid.uuid4())


def generate_api_key(prefix: str = "nexus") -> str:
    return f"{prefix}_{generate_secure_token(32)}"
    return f"{prefix}_{generate_secure_token(32)}"


def encrypt_data(data: str) -> str:
    if not data:
        return ""
    return _get_fernet().encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    if not encrypted_data:
        return ""
    try:
        return _get_fernet().decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {e}")


def hash_sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def hmac_sha256(key: str, message: str) -> str:
    return hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def mask_email(email: str) -> str:
    if '@' not in email:
        return email
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***' + local[-1]
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    if len(phone) <= 6:
        return '*' * len(phone)
    # عرض أول 6 أحرف ثم إخفاء 4 ثم عرض آخر 3
    visible_start = 6
    visible_end = 3
    if len(phone) <= visible_start + visible_end:
        return phone[:3] + '*' * (len(phone) - 6) + phone[-3:]
    return phone[:visible_start] + '*' * 4 + phone[-visible_end:]


__all__ = [
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "generate_token",
    "generate_refresh_token",
    "verify_token",
    "decode_token",
    "get_token_remaining_time",
    "generate_secure_token",
    "generate_secure_uuid",
    "generate_api_key",
    "encrypt_data",
    "decrypt_data",
    "hash_sha256",
    "hmac_sha256",
    "constant_time_compare",
    "mask_email",
    "mask_phone",
]

# تعديل دالة generate_api_key
def generate_api_key(prefix: str = "nexus") -> str:
    return f"{prefix}_{generate_secure_token(32)}"
    token = generate_secure_token(32)
    return f"{prefix}_{token}"

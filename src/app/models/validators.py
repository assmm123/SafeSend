"""
دوالب التحقق من صحة البيانات
Data Validation Utilities

يوفر هذا الملف دوال التحقق من:
- البريد الإلكتروني
- اسم المستخدم
- رقم الهاتف
- الروابط
- المبالغ المالية
- UUID
- عناوين TRON
- تطهير المدخلات
"""

import re
import html
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple, Union


# ============================================
# أنماط التحقق - Validation Patterns
# ============================================

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+$',
    re.IGNORECASE
)

USERNAME_REGEX = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{2,31}$')

PHONE_REGEX = re.compile(r'^\+?[0-9]{7,15}$')

URL_REGEX = re.compile(
    r'^(https?|ftp)://[^\s/$.?#].[^\s]*$',
    re.IGNORECASE
)

UUID_REGEX = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

TRON_ADDRESS_REGEX = re.compile(r'^T[a-zA-Z0-9]{33}$')

HEX_COLOR_REGEX = re.compile(r'^#?([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$')


# ============================================
# دوال التحقق - Validation Functions
# ============================================

def validate_email(email: str) -> Tuple[bool, str]:
    """
    التحقق من صحة البريد الإلكتروني
    Validate email address
    
    Args:
        email (str): البريد الإلكتروني / Email address
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    
    Example:
        >>> valid, msg = validate_email("user@example.com")
        >>> print(valid)  # True
    """
    if not email:
        return False, "Email is required"
    
    if not isinstance(email, str):
        return False, "Email must be a string"
    
    email = email.strip().lower()
    
    if len(email) > 254:
        return False, "Email is too long (max 254 characters)"
    
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"
    
    # التحقق من النطاقات المحظورة
    blocked_domains = {'example.com', 'test.com', 'localhost'}
    domain = email.split('@')[1]
    if domain in blocked_domains:
        return False, "Email domain not allowed"
    
    return True, email


def validate_username(username: str) -> Tuple[bool, str]:
    """
    التحقق من صحة اسم المستخدم
    Validate username
    
    القواعد:
    - يبدأ بحرف إنجليزي
    - يحتوي على أحرف وأرقام وشرطة سفلية فقط
    - الطول بين 3 و 32 حرفاً
    
    Rules:
    - Starts with a letter
    - Contains only letters, numbers, and underscore
    - Length between 3 and 32 characters
    
    Args:
        username (str): اسم المستخدم / Username
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    """
    if not username:
        return False, "Username is required"
    
    if not isinstance(username, str):
        return False, "Username must be a string"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 32:
        return False, "Username must be at most 32 characters"
    
    if not USERNAME_REGEX.match(username):
        return False, "Username must start with a letter and contain only letters, numbers, and underscores"
    
    # قائمة الكلمات المحظورة
    reserved_words = {'admin', 'root', 'system', 'nexus', 'support', 'owner'}
    if username.lower() in reserved_words:
        return False, "This username is reserved"
    
    return True, username


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    التحقق من صحة رقم الهاتف
    Validate phone number
    
    Args:
        phone (str): رقم الهاتف / Phone number
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    """
    if not phone:
        return False, "Phone number is required"
    
    if not isinstance(phone, str):
        return False, "Phone must be a string"
    
    # إزالة المسافات والشرطات
    phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
    
    if not PHONE_REGEX.match(phone):
        return False, "Invalid phone number format"
    
    return True, phone


def validate_url(url: str) -> Tuple[bool, str]:
    """
    التحقق من صحة الرابط
    Validate URL
    
    Args:
        url (str): الرابط / URL
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    """
    if not url:
        return False, "URL is required"
    
    if not isinstance(url, str):
        return False, "URL must be a string"
    
    url = url.strip()
    
    if len(url) > 2048:
        return False, "URL is too long"
    
    if not URL_REGEX.match(url):
        return False, "Invalid URL format"
    
    return True, url


def validate_amount(
    amount: Union[str, int, float, Decimal],
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    decimal_places: int = 2
) -> Tuple[bool, str, Optional[Decimal]]:
    """
    التحقق من صحة المبلغ المالي
    Validate monetary amount
    
    Args:
        amount: المبلغ / Amount
        min_amount: الحد الأدنى / Minimum amount
        max_amount: الحد الأقصى / Maximum amount
        decimal_places: عدد المنازل العشرية / Decimal places
    
    Returns:
        Tuple[bool, str, Optional[Decimal]]: (هل صحيح؟, رسالة, القيمة)
    """
    if amount is None:
        return False, "Amount is required", None
    
    try:
        if isinstance(amount, Decimal):
            value = amount
        else:
            value = Decimal(str(amount))
        
        if value <= 0:
            return False, "Amount must be greater than zero", None
        
        if min_amount and value < min_amount:
            return False, f"Amount must be at least {min_amount}", None
        
        if max_amount and value > max_amount:
            return False, f"Amount must be at most {max_amount}", None
        
        # التحقق من المنازل العشرية
        parts = str(value).split('.')
        if len(parts) > 1 and len(parts[1]) > decimal_places:
            return False, f"Amount cannot have more than {decimal_places} decimal places", None
        
        return True, "Valid amount", value
        
    except (InvalidOperation, ValueError):
        return False, "Invalid amount format", None


def validate_uuid(uuid_str: str) -> Tuple[bool, str]:
    """
    التحقق من صحة UUID
    Validate UUID string
    
    Args:
        uuid_str (str): نص UUID / UUID string
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    """
    if not uuid_str:
        return False, "UUID is required"
    
    if not isinstance(uuid_str, str):
        return False, "UUID must be a string"
    
    if not UUID_REGEX.match(uuid_str.strip()):
        return False, "Invalid UUID format"
    
    try:
        uuid.UUID(uuid_str)
        return True, uuid_str
    except ValueError:
        return False, "Invalid UUID"


def validate_tron_address(address: str) -> Tuple[bool, str]:
    """
    التحقق من صحة عنوان TRON
    Validate TRON address
    
    عنوان TRON يبدأ بـ T ويتكون من 34 حرفاً.
    TRON address starts with T and is 34 characters long.
    
    Args:
        address (str): عنوان TRON / TRON address
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    """
    if not address:
        return False, "TRON address is required"
    
    if not isinstance(address, str):
        return False, "Address must be a string"
    
    address = address.strip()
    
    if not TRON_ADDRESS_REGEX.match(address):
        return False, "Invalid TRON address format (must start with 'T' and be 34 characters)"
    
    return True, address


def validate_hex_color(color: str) -> Tuple[bool, str]:
    """
    التحقق من صحة كود لون HEX
    Validate HEX color code
    
    Args:
        color (str): كود اللون / Color code
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    """
    if not color:
        return False, "Color code is required"
    
    if not HEX_COLOR_REGEX.match(color.strip()):
        return False, "Invalid HEX color format (e.g., #FF0000 or FF0000)"
    
    return True, color.strip()


def validate_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> Tuple[bool, str]:
    """
    التحقق من طول النص
    Validate string length
    
    Args:
        value (str): النص / String
        min_length (Optional[int]): الحد الأدنى / Minimum length
        max_length (Optional[int]): الحد الأقصى / Maximum length
    
    Returns:
        Tuple[bool, str]: (هل صحيح؟, رسالة) / (Is valid?, message)
    """
    if value is None:
        return False, "Value is required"
    
    if not isinstance(value, str):
        value = str(value)
    
    length = len(value)
    
    if min_length and length < min_length:
        return False, f"Value must be at least {min_length} characters"
    
    if max_length and length > max_length:
        return False, f"Value must be at most {max_length} characters"
    
    return True, value


# ============================================
# دوال التطهير - Sanitization Functions
# ============================================

def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    تطهير النص من الأحرف الضارة والمسافات الزائدة
    Sanitize string from harmful characters and extra spaces
    
    Args:
        text (str): النص المراد تطهيره / Text to sanitize
        max_length (Optional[int]): الحد الأقصى للطول / Maximum length
    
    Returns:
        str: النص المطهر / Sanitized text
    """
    if not text:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    # إزالة HTML tags
    text = html.escape(text)
    
    # إزالة أحرف التحكم
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # إزالة المسافات الزائدة
    text = ' '.join(text.split())
    
    # تقليم النص
    text = text.strip()
    
    # قص النص إذا تجاوز الحد الأقصى
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def sanitize_email(email: str) -> str:
    """
    تطهير البريد الإلكتروني
    Sanitize email address
    
    Args:
        email (str): البريد الإلكتروني / Email
    
    Returns:
        str: البريد المطهر / Sanitized email
    """
    if not email:
        return ""
    
    return email.strip().lower()


def sanitize_username(username: str) -> str:
    """
    تطهير اسم المستخدم
    Sanitize username
    
    Args:
        username (str): اسم المستخدم / Username
    
    Returns:
        str: الاسم المطهر / Sanitized username
    """
    if not username:
        return ""
    
    # إزالة المسافات والأحرف غير المسموحة
    username = username.strip()
    username = re.sub(r'[^a-zA-Z0-9_]', '', username)
    
    return username


def sanitize_json(data: Any) -> Any:
    """
    تطهير بيانات JSON من القيم الضارة
    Sanitize JSON data from harmful values
    
    Args:
        data (Any): البيانات / Data
    
    Returns:
        Any: البيانات المطهرة / Sanitized data
    """
    if data is None:
        return None
    
    if isinstance(data, str):
        return sanitize_string(data)
    
    if isinstance(data, dict):
        return {k: sanitize_json(v) for k, v in data.items()}
    
    if isinstance(data, list):
        return [sanitize_json(item) for item in data]
    
    return data


# ============================================
# دوال التحقق المجمعة - Bulk Validation
# ============================================

def validate_required_fields(data: dict, required_fields: list) -> Tuple[bool, list]:
    """
    التحقق من وجود جميع الحقول المطلوبة
    Validate that all required fields are present
    
    Args:
        data (dict): البيانات / Data dictionary
        required_fields (list): الحقول المطلوبة / Required fields
    
    Returns:
        Tuple[bool, list]: (هل جميعها موجودة؟, الحقول المفقودة)
    """
    missing = [field for field in required_fields if field not in data or data[field] is None]
    return len(missing) == 0, missing


def validate_all(data: dict, rules: dict) -> Tuple[bool, dict]:
    """
    التحقق من البيانات وفق قواعد محددة
    Validate data against defined rules
    
    Args:
        data (dict): البيانات / Data dictionary
        rules (dict): القواعد لكل حقل / Rules per field
            Example: {"email": "email", "username": "username", "amount": "amount"}
    
    Returns:
        Tuple[bool, dict]: (هل الكل صحيح؟, قاموس الأخطاء)
    """
    errors = {}
    
    validators_map = {
        "email": validate_email,
        "username": validate_username,
        "phone": validate_phone,
        "url": validate_url,
        "uuid": validate_uuid,
        "tron": validate_tron_address,
    }
    
    for field, rule in rules.items():
        value = data.get(field)
        validator = validators_map.get(rule)
        
        if validator:
            valid, msg = validator(value) if value else (False, f"{field} is required")
            if not valid:
                errors[field] = msg
    
    return len(errors) == 0, errors


__all__ = [
    # Validation
    "validate_email",
    "validate_username",
    "validate_phone",
    "validate_url",
    "validate_amount",
    "validate_uuid",
    "validate_tron_address",
    "validate_hex_color",
    "validate_length",
    # Sanitization
    "sanitize_string",
    "sanitize_email",
    "sanitize_username",
    "sanitize_json",
    # Bulk
    "validate_required_fields",
    "validate_all",
    # Constants
    "EMAIL_REGEX",
    "USERNAME_REGEX",
    "PHONE_REGEX",
    "URL_REGEX",
    "TRON_ADDRESS_REGEX",
]

"""
دوال مساعدة عامة للنظام
General Helper Utilities for the System

يوفر هذا الملف دوال مساعدة لـ:
- الوقت والتاريخ
- معالجة النصوص
- الأرقام والعملات
- الملفات والمجلدات
- القوائم والقواميس
- الشبكة والمتفرقات
"""

import hashlib
import json
import os
import re
import secrets
import string
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Tuple, TypeVar, Union
from urllib.parse import urljoin, urlparse

T = TypeVar('T')


# ============================================
# دوال الوقت والتاريخ - Time & Date Utilities
# ============================================

def utc_now() -> datetime:
    """
    الحصول على الوقت الحالي بتوقيت UTC
    Get current UTC datetime
    
    Returns:
        datetime: الوقت الحالي بتوقيت UTC
    """
    return datetime.now(timezone.utc)


def iso_format(dt: Optional[datetime] = None) -> str:
    """
    تنسيق التاريخ بصيغة ISO 8601
    Format datetime as ISO 8601 string
    
    Args:
        dt (Optional[datetime]): التاريخ (UTC الآن إذا لم يحدد)
    
    Returns:
        str: التاريخ بصيغة ISO
    """
    if dt is None:
        dt = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso_datetime(date_str: str) -> Optional[datetime]:
    """
    تحويل نص ISO إلى كائن datetime
    Parse ISO string to datetime object
    
    Args:
        date_str (str): النص بصيغة ISO
    
    Returns:
        Optional[datetime]: كائن datetime أو None إذا فشل
    """
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def time_ago(dt: datetime, locale: str = 'ar') -> str:
    """
    حساب المدة منذ تاريخ معين بصيغة نصية
    Calculate time ago in human readable format
    
    Args:
        dt (datetime): التاريخ المطلوب
        locale (str): اللغة ('ar' أو 'en')
    
    Returns:
        str: المدة بصيغة نصية
    
    Example:
        >>> time_ago(datetime.now() - timedelta(hours=2))
        'منذ ساعتين'
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = utc_now()
    diff = now - dt
    
    seconds = int(diff.total_seconds())
    
    if seconds < 0:
        return 'الآن' if locale == 'ar' else 'just now'
    elif seconds < 60:
        return 'الآن' if locale == 'ar' else 'just now'
    elif seconds < 3600:
        minutes = seconds // 60
        if locale == 'ar':
            return f'منذ دقيقة' if minutes == 1 else f'منذ دقيقتين' if minutes == 2 else f'منذ {minutes} دقائق'
        else:
            return f'{minutes} minute ago' if minutes == 1 else f'{minutes} minutes ago'
    elif seconds < 86400:
        hours = seconds // 3600
        if locale == 'ar':
            return f'منذ ساعة' if hours == 1 else f'منذ ساعتين' if hours == 2 else f'منذ {hours} ساعات'
        else:
            return f'{hours} hour ago' if hours == 1 else f'{hours} hours ago'
    elif seconds < 2592000:
        days = seconds // 86400
        if locale == 'ar':
            return f'منذ يوم' if days == 1 else f'منذ يومين' if days == 2 else f'منذ {days} أيام'
        else:
            return f'{days} day ago' if days == 1 else f'{days} days ago'
    elif seconds < 31536000:
        months = seconds // 2592000
        if locale == 'ar':
            return f'منذ شهر' if months == 1 else f'منذ شهرين' if months == 2 else f'منذ {months} أشهر'
        else:
            return f'{months} month ago' if months == 1 else f'{months} months ago'
    else:
        years = seconds // 31536000
        if locale == 'ar':
            return f'منذ سنة' if years == 1 else f'منذ سنتين' if years == 2 else f'منذ {years} سنوات'
        else:
            return f'{years} year ago' if years == 1 else f'{years} years ago'


def is_expired(timestamp: datetime, ttl_seconds: int) -> bool:
    """
    التحقق مما إذا كان الطابع الزمني قد انتهت صلاحيته
    Check if timestamp is expired
    
    Args:
        timestamp (datetime): الطابع الزمني
        ttl_seconds (int): مدة الصلاحية بالثواني
    
    Returns:
        bool: True إذا انتهت الصلاحية
    """
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    expiry_time = timestamp + timedelta(seconds=ttl_seconds)
    return utc_now() > expiry_time


def add_seconds(dt: datetime, seconds: int) -> datetime:
    """
    إضافة ثواني إلى تاريخ
    Add seconds to datetime
    
    Args:
        dt (datetime): التاريخ
        seconds (int): عدد الثواني
    
    Returns:
        datetime: التاريخ الجديد
    """
    return dt + timedelta(seconds=seconds)


def start_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    الحصول على بداية اليوم (00:00:00)
    Get start of day
    
    Args:
        dt (Optional[datetime]): التاريخ (اليوم إذا لم يحدد)
    
    Returns:
        datetime: بداية اليوم
    """
    if dt is None:
        dt = utc_now()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    الحصول على نهاية اليوم (23:59:59.999999)
    Get end of day
    
    Args:
        dt (Optional[datetime]): التاريخ (اليوم إذا لم يحدد)
    
    Returns:
        datetime: نهاية اليوم
    """
    if dt is None:
        dt = utc_now()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


# ============================================
# دوال النصوص - String Utilities
# ============================================

def slugify(text: str, allow_unicode: bool = True, separator: str = '-') -> str:
    """
    تحويل النص إلى slug صالح للـ URL
    Convert text to URL-friendly slug
    
    Args:
        text (str): النص المراد تحويله
        allow_unicode (bool): السماح بالحروف العربية
        separator (str): الفاصل بين الكلمات
    
    Returns:
        str: النص المحول
    
    Example:
        >>> slugify('مرحبا بالعالم!')
        'مرحبا-بالعالم'
    """
    if allow_unicode:
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'[^\w\s' + separator + ']', '', text, flags=re.UNICODE)
    else:
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r'[^\w\s' + separator + ']', '', text)
    
    text = text.strip().lower()
    return re.sub(r'[-\s]+', separator, text)


def truncate(text: str, length: int, suffix: str = '...') -> str:
    """
    قص النص إلى طول محدد مع إضافة لاحقة
    Truncate text to specified length with suffix
    
    Args:
        text (str): النص المراد قصه
        length (int): الطول الأقصى
        suffix (str): اللاحقة المضافة
    
    Returns:
        str: النص المقصوص
    """
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix


def remove_accents(text: str) -> str:
    """
    إزالة الحركات والتشكيل من النص العربي
    Remove diacritics from Arabic text
    
    Args:
        text (str): النص مع التشكيل
    
    Returns:
        str: النص بدون تشكيل
    """
    arabic_diacritics = re.compile(r'[\u064B-\u0652\u0670]')
    return arabic_diacritics.sub('', text)


def mask_string(
    text: str,
    visible_start: int = 2,
    visible_end: int = 2,
    mask_char: str = '*'
) -> str:
    """
    إخفاء جزء من النص مع إظهار البداية والنهاية
    Mask part of string showing start and end
    
    Args:
        text (str): النص المراد إخفاؤه
        visible_start (int): عدد الأحرف الظاهرة من البداية
        visible_end (int): عدد الأحرف الظاهرة من النهاية
        mask_char (str): حرف الإخفاء
    
    Returns:
        str: النص المخفي
    
    Example:
        >>> mask_string('ahmed@gmail.com', 3, 4)
        'ahm***.com'
    """
    if not text:
        return ''
    if len(text) <= visible_start + visible_end:
        return mask_char * len(text)
    return text[:visible_start] + mask_char * (len(text) - visible_start - visible_end) + text[-visible_end:]


def random_string(length: int = 16, include_punctuation: bool = False) -> str:
    """
    توليد نص عشوائي آمن
    Generate secure random string
    
    Args:
        length (int): الطول المطلوب
        include_punctuation (bool): تضمين علامات الترقيم
    
    Returns:
        str: النص العشوائي
    """
    chars = string.ascii_letters + string.digits
    if include_punctuation:
        chars += '!@#$%^&*'
    return ''.join(secrets.choice(chars) for _ in range(length))


def clean_html(text: str) -> str:
    """
    إزالة وسوم HTML من النص
    Remove HTML tags from text
    
    Args:
        text (str): النص المحتوي على HTML
    
    Returns:
        str: النص النظيف
    """
    import html
    text = html.unescape(text)
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def extract_mentions(text: str) -> List[str]:
    """
    استخراج الإشارات (@username) من النص
    Extract @mentions from text
    
    Args:
        text (str): النص
    
    Returns:
        List[str]: قائمة المستخدمين المشار إليهم
    """
    mention_pattern = re.compile(r'@([a-zA-Z0-9_]{3,32})')
    return mention_pattern.findall(text)


def extract_hashtags(text: str) -> List[str]:
    """
    استخراج الوسوم (#hashtag) من النص
    Extract #hashtags from text
    
    Args:
        text (str): النص
    
    Returns:
        List[str]: قائمة الوسوم
    """
    hashtag_pattern = re.compile(r'#([\u0600-\u06FFa-zA-Z0-9_]{2,50})')
    return hashtag_pattern.findall(text)


# ============================================
# دوال الأرقام والعملات - Number & Currency Utilities
# ============================================

def format_number(value: Union[int, float, Decimal], decimals: int = 0) -> str:
    """
    تنسيق رقم مع فواصل الآلاف
    Format number with thousand separators
    
    Args:
        value: الرقم
        decimals (int): عدد المنازل العشرية
    
    Returns:
        str: الرقم المنسق
    """
    if decimals > 0:
        return f"{value:,.{decimals}f}"
    return f"{value:,.0f}"


def format_currency(
    amount: Union[int, float, Decimal],
    currency: str = 'USD',
    locale: str = 'en'
) -> str:
    """
    تنسيق مبلغ مالي
    Format currency amount
    
    Args:
        amount: المبلغ
        currency (str): رمز العملة (USD, SAR, AED)
        locale (str): اللغة
    
    Returns:
        str: المبلغ المنسق
    """
    symbols = {
        'USD': '$', 'SAR': '﷼', 'AED': 'د.إ', 'EUR': '€', 'GBP': '£'
    }
    symbol = symbols.get(currency.upper(), currency)
    
    formatted = format_number(amount, 2)
    
    if locale == 'ar':
        if currency == 'SAR':
            return f"{formatted} {symbol}"
        return f"{formatted} {symbol}"
    else:
        return f"{symbol}{formatted}"


def parse_number(text: str) -> Optional[Decimal]:
    """
    تحويل نص إلى رقم مع دعم الفواصل
    Parse string to number with separator support
    
    Args:
        text (str): النص الرقمي
    
    Returns:
        Optional[Decimal]: الرقم أو None
    """
    if not text:
        return None
    clean = re.sub(r'[^\d.,\-]', '', text)
    clean = clean.replace(',', '')
    try:
        return Decimal(clean)
    except InvalidOperation:
        return None


def percentage(value: Union[int, float], total: Union[int, float], decimals: int = 1) -> float:
    """
    حساب النسبة المئوية
    Calculate percentage
    
    Args:
        value: القيمة
        total: المجموع الكلي
        decimals (int): عدد المنازل العشرية
    
    Returns:
        float: النسبة المئوية
    """
    if total == 0:
        return 0.0
    result = (value / total) * 100
    return round(result, decimals)


def round_to(value: Union[int, float, Decimal], decimals: int = 2) -> Decimal:
    """
    تقريب رقم إلى عدد محدد من المنازل العشرية
    Round number to specified decimal places
    
    Args:
        value: الرقم
        decimals (int): عدد المنازل
    
    Returns:
        Decimal: الرقم المقرب
    """
    if isinstance(value, Decimal):
        return value.quantize(Decimal('1.' + '0' * decimals))
    return Decimal(str(value)).quantize(Decimal('1.' + '0' * decimals))


def clamp(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
    """
    تحديد قيمة بين حد أدنى وأقصى
    Clamp value between min and max
    
    Args:
        value: القيمة
        min_val: الحد الأدنى
        max_val: الحد الأقصى
    
    Returns:
        القيمة المحددة
    """
    return max(min_val, min(value, max_val))


# ============================================
# دوال الملفات والمجلدات - File & Directory Utilities
# ============================================

def format_file_size(size_bytes: int) -> str:
    """
    تنسيق حجم الملف إلى صيغة مقروءة
    Format file size to human readable format
    
    Args:
        size_bytes (int): الحجم بالبايت
    
    Returns:
        str: الحجم المنسق
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} EB"


def get_file_extension(filename: str) -> str:
    """
    استخراج امتداد الملف
    Get file extension
    
    Args:
        filename (str): اسم الملف
    
    Returns:
        str: الامتداد (مع النقطة)
    """
    return os.path.splitext(filename)[1].lower()


def safe_filename(filename: str) -> str:
    """
    تحويل اسم الملف إلى اسم آمن
    Convert filename to safe filename
    
    Args:
        filename (str): اسم الملف الأصلي
    
    Returns:
        str: اسم الملف الآمن
    """
    name, ext = os.path.splitext(filename)
    name = slugify(name, allow_unicode=False, separator='_')
    if not name:
        name = random_string(8)
    return name + ext.lower()


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    التأكد من وجود مجلد وإنشائه إذا لم يوجد
    Ensure directory exists, create if not
    
    Args:
        path: مسار المجلد
    
    Returns:
        Path: كائن Path للمجلد
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_file_chunks(
    file_path: Union[str, Path],
    chunk_size: int = 8192
) -> Generator[bytes, None, None]:
    """
    قراءة ملف على شكل قطع (للملفات الكبيرة)
    Read file in chunks (for large files)
    
    Args:
        file_path: مسار الملف
        chunk_size (int): حجم القطعة بالبايت
    
    Yields:
        bytes: قطعة من الملف
    """
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            yield chunk


def get_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
    """
    حساب تجزئة الملف
    Calculate file hash
    
    Args:
        file_path: مسار الملف
        algorithm (str): خوارزمية التجزئة (sha256, md5)
    
    Returns:
        str: قيمة التجزئة
    """
    hash_func = hashlib.new(algorithm)
    for chunk in read_file_chunks(file_path):
        hash_func.update(chunk)
    return hash_func.hexdigest()


def list_files(
    directory: Union[str, Path],
    pattern: str = '*',
    recursive: bool = False
) -> List[Path]:
    """
    سرد الملفات في مجلد
    List files in directory
    
    Args:
        directory: مسار المجلد
        pattern (str): نمط الملفات (مثل *.py)
        recursive (bool): البحث في المجلدات الفرعية
    
    Returns:
        List[Path]: قائمة الملفات
    """
    path = Path(directory)
    if recursive:
        return list(path.rglob(pattern))
    return list(path.glob(pattern))


# ============================================
# دوال القوائم والقواميس - List & Dict Utilities
# ============================================

def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """
    تقسيم قائمة إلى أجزاء متساوية
    Split list into chunks
    
    Args:
        lst: القائمة
        chunk_size (int): حجم القطعة
    
    Returns:
        List[List[T]]: قائمة القطع
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_list(nested_list: List[Any]) -> List[Any]:
    """
    تسطيح قائمة متداخلة
    Flatten nested list
    
    Args:
        nested_list: القائمة المتداخلة
    
    Returns:
        List[Any]: قائمة مسطحة
    """
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    دمج قاموسين بشكل عميق
    Deep merge two dictionaries
    
    Args:
        dict1: القاموس الأول
        dict2: القاموس الثاني
    
    Returns:
        Dict: القاموس المدمج
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_nested(data: Dict, path: str, default: Any = None, separator: str = '.') -> Any:
    """
    الوصول إلى قيمة متداخلة باستخدام مسار
    Get nested value using dot notation path
    
    Args:
        data (Dict): القاموس
        path (str): المسار (مثال: user.address.city)
        default (Any): القيمة الافتراضية
        separator (str): الفاصل
    
    Returns:
        Any: القيمة أو الافتراضية
    """
    keys = path.split(separator)
    current = data
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError, IndexError):
        return default


def set_nested(data: Dict, path: str, value: Any, separator: str = '.') -> Dict:
    """
    تعيين قيمة متداخلة باستخدام مسار
    Set nested value using dot notation path
    
    Args:
        data (Dict): القاموس
        path (str): المسار
        value (Any): القيمة
        separator (str): الفاصل
    
    Returns:
        Dict: القاموس بعد التعديل
    """
    keys = path.split(separator)
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return data


def group_by(lst: List[Dict], key: str) -> Dict[Any, List[Dict]]:
    """
    تجميع قائمة قواميس حسب مفتاح
    Group list of dicts by key
    
    Args:
        lst: قائمة القواميس
        key (str): مفتاح التجميع
    
    Returns:
        Dict: القواميس مجمعة
    """
    result = {}
    for item in lst:
        group_key = item.get(key)
        if group_key not in result:
            result[group_key] = []
        result[group_key].append(item)
    return result


def unique_list(lst: List[T]) -> List[T]:
    """
    إزالة العناصر المكررة مع الحفاظ على الترتيب
    Remove duplicates while preserving order
    
    Args:
        lst: القائمة
    
    Returns:
        List[T]: قائمة بدون تكرار
    """
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


# ============================================
# دوال الشبكة والـ API - Network & API Utilities
# ============================================

def is_valid_url(url: str) -> bool:
    """
    التحقق من صحة رابط URL
    Validate URL format
    
    Args:
        url (str): الرابط
    
    Returns:
        bool: True إذا كان صالحاً
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False


def url_join(base: str, *parts: str) -> str:
    """
    دمج أجزاء رابط URL
    Join URL parts
    
    Args:
        base: الرابط الأساسي
        *parts: الأجزاء الإضافية
    
    Returns:
        str: الرابط الكامل
    """
    result = base
    for part in parts:
        result = urljoin(result + '/', str(part))
    return result


def is_valid_ip(ip: str) -> bool:
    """
    التحقق من صحة عنوان IP (IPv4)
    Validate IPv4 address
    
    
  Args:
        ip (str): عنوان IP
    
    Returns:
        bool: True إذا كان صالحاً
    """
    pattern = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    return bool(pattern.match(ip))


def parse_query_string(query_string: str) -> Dict[str, str]:
    """
    تحويل query string إلى قاموس
    Parse query string to dict
    
    Args:
        query_string (str): النص (مثال: key1=value1&key2=value2)
    
    Returns:
        Dict[str, str]: القاموس
    """
    from urllib.parse import parse_qs
    result = parse_qs(query_string)
    return {k: v[0] if len(v) == 1 else v for k, v in result.items()}


# ============================================
# دوال متنوعة - Miscellaneous Utilities
# ============================================

def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple = (Exception,)
) -> Callable:
    """
    ديكوراتر لإعادة محاولة دالة عند الفشل
    Decorator to retry function on failure
    
    Args:
        max_retries (int): عدد المحاولات القصوى
        delay (float): التأخير الأولي بالثواني
        backoff (float): مضاعفة التأخير
        exceptions (Tuple): الاستثناءات التي تسبب إعادة المحاولة
    
    Returns:
        Callable: الدالة المغلفة
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator


def is_valid_json(text: str) -> bool:
    """
    التحقق من صحة نص JSON
    Validate JSON string
    
    Args:
        text (str): النص
    
    Returns:
        bool: True إذا كان JSON صالح
    """
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def generate_id(prefix: str = '', length: int = 12) -> str:
    """
    توليد معرف فريد
    Generate unique ID
    
    Args:
        prefix (str): بادئة
        length (int): الطول
    
    Returns:
        str: المعرف الفريد
    """
    unique = random_string(length)
    return f"{prefix}_{unique}" if prefix else unique


def cached_property(func: Callable) -> property:
    """
    ديكوراتر لتخزين قيمة property مؤقتاً
    Decorator to cache property value
    
    Args:
        func (Callable): الدالة
    
    Returns:
        property: property مخزنة
    """
    attr_name = f'_cached_{func.__name__}'
    
    @property
    @wraps(func)
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    
    return wrapper


def to_bool(value: Any) -> bool:
    """
    تحويل قيمة إلى boolean
    Convert value to boolean
    
    Args:
        value: القيمة
    
    Returns:
        bool: القيمة المحولة
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'y')
    return bool(value)


def merge_dicts(*dicts: Dict) -> Dict:
    """
    دمج عدة قواميس
    Merge multiple dictionaries
    
    Args:
        *dicts: القواميس المراد دمجها
    
    Returns:
        Dict: القاموس المدمج
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


__all__ = [
    # Time & Date
    'utc_now', 'iso_format', 'parse_iso_datetime', 'time_ago', 'is_expired',
    'add_seconds', 'start_of_day', 'end_of_day',
    # String
    'slugify', 'truncate', 'remove_accents', 'mask_string', 'random_string',
    'clean_html', 'extract_mentions', 'extract_hashtags',
    # Number & Currency
    'format_number', 'format_currency', 'parse_number', 'percentage',
    'round_to', 'clamp',
    # File & Directory
    'format_file_size', 'get_file_extension', 'safe_filename', 'ensure_directory',
    'read_file_chunks', 'get_file_hash', 'list_files',
    # List & Dict
    'chunk_list', 'flatten_list', 'deep_merge', 'get_nested', 'set_nested',
    'group_by', 'unique_list',
    # Network
    'is_valid_url', 'url_join', 'is_valid_ip', 'parse_query_string',
    # Miscellaneous
    'retry', 'is_valid_json', 'generate_id', 'cached_property', 'to_bool', 'merge_dicts',
]

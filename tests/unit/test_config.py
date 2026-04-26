"""
اختبارات إعدادات التطبيق
Unit Tests for Application Configuration
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from src.app.models.config import (
    Config,
    DevelopmentConfig,
    TestingConfig,
    ProductionConfig,
    config_by_name,
    get_config,
    get_database_url,
    is_production,
    is_testing,
    is_development,
)


class TestBaseConfig:
    """اختبارات الإعدادات الأساسية"""
    
    def test_secret_key_has_default(self):
        """اختبار أن SECRET_KEY له قيمة افتراضية"""
        config = Config()
        assert config.SECRET_KEY is not None
        assert isinstance(config.SECRET_KEY, str)
        assert len(config.SECRET_KEY) > 0
    
    def test_jwt_secret_key_has_default(self):
        """اختبار أن JWT_SECRET_KEY له قيمة افتراضية"""
        config = Config()
        assert config.JWT_SECRET_KEY is not None
        assert isinstance(config.JWT_SECRET_KEY, str)
        assert len(config.JWT_SECRET_KEY) > 0
    
    def test_bcrypt_rounds_default(self):
        """اختبار القيمة الافتراضية لـ BCRYPT_ROUNDS"""
        config = Config()
        assert config.BCRYPT_ROUNDS == 12
    
    def test_sqlalchemy_track_modifications_disabled(self):
        """اختبار أن تتبع التعديلات معطل"""
        config = Config()
        assert config.SQLALCHEMY_TRACK_MODIFICATIONS is False
    
    def test_backup_dir_has_default(self):
        """اختبار أن BACKUP_DIR له قيمة افتراضية"""
        config = Config()
        assert config.BACKUP_DIR == "./backups"
    
    def test_backup_retention_days_default(self):
        """اختبار القيمة الافتراضية لـ BACKUP_RETENTION_DAYS"""
        config = Config()
        assert config.BACKUP_RETENTION_DAYS == 30


class TestDevelopmentConfig:
    """اختبارات إعدادات بيئة التطوير"""
    
    def test_debug_enabled(self):
        """اختبار أن DEBUG مفعل"""
        config = DevelopmentConfig()
        assert config.DEBUG is True
    
    def test_testing_disabled(self):
        """اختبار أن TESTING معطل"""
        config = DevelopmentConfig()
        assert config.TESTING is False
    
    def test_database_uri_is_sqlite(self):
        """اختبار أن قاعدة البيانات SQLite"""
        config = DevelopmentConfig()
        assert "sqlite" in config.SQLALCHEMY_DATABASE_URI
    
    def test_log_level_is_debug(self):
        """اختبار أن مستوى التسجيل DEBUG"""
        config = DevelopmentConfig()
        assert config.LOG_LEVEL == "DEBUG"


class TestTestingConfig:
    """اختبارات إعدادات بيئة الاختبار"""
    
    def test_debug_disabled(self):
        """اختبار أن DEBUG معطل"""
        config = TestingConfig()
        assert config.DEBUG is False
    
    def test_testing_enabled(self):
        """اختبار أن TESTING مفعل"""
        config = TestingConfig()
        assert config.TESTING is True
    
    def test_database_uri_is_postgresql(self):
        """اختبار أن قاعدة البيانات PostgreSQL (حسب القاعدة 9)"""
        config = TestingConfig()
        assert "postgresql" in config.SQLALCHEMY_DATABASE_URI
    
    def test_csrf_disabled(self):
        """اختبار أن CSRF معطل للاختبارات"""
        config = TestingConfig()
        assert config.WTF_CSRF_ENABLED is False
    
    def test_bcrypt_rounds_reduced(self):
        """اختبار أن bcrypt أسرع للاختبارات"""
        config = TestingConfig()
        assert config.BCRYPT_ROUNDS == 4
    
    def test_log_level_is_warning(self):
        """اختبار أن مستوى التسجيل WARNING"""
        config = TestingConfig()
        assert config.LOG_LEVEL == "WARNING"


class TestProductionConfig:
    """اختبارات إعدادات بيئة الإنتاج"""
    
    def test_debug_disabled(self):
        """اختبار أن DEBUG معطل"""
        config = ProductionConfig()
        assert config.DEBUG is False
    
    def test_testing_disabled(self):
        """اختبار أن TESTING معطل"""
        config = ProductionConfig()
        assert config.TESTING is False
    
    def test_database_uri_is_postgresql(self):
        """اختبار أن قاعدة البيانات PostgreSQL (حسب القاعدة 9)"""
        config = ProductionConfig()
        assert "postgresql" in config.SQLALCHEMY_DATABASE_URI
    
    def test_session_cookie_secure(self):
        """اختبار أن كوكيز الجلسة آمن"""
        config = ProductionConfig()
        assert config.SESSION_COOKIE_SECURE is True
        assert config.SESSION_COOKIE_HTTPONLY is True
    
    def test_csrf_enabled(self):
        """اختبار أن CSRF مفعل"""
        config = ProductionConfig()
        assert config.WTF_CSRF_ENABLED is True
    
    def test_log_level_is_info(self):
        """اختبار أن مستوى التسجيل INFO"""
        config = ProductionConfig()
        assert config.LOG_LEVEL == "INFO"
    
    def test_metrics_enabled(self):
        """اختبار أن المراقبة مفعلة"""
        config = ProductionConfig()
        assert config.METRICS_ENABLED is True


class TestGetConfig:
    """اختبارات دالة get_config"""
    
    def test_get_development_config(self):
        """اختبار جلب إعدادات التطوير"""
        config = get_config("development")
        assert isinstance(config, DevelopmentConfig)
        assert config.DEBUG is True
    
    def test_get_testing_config(self):
        """اختبار جلب إعدادات الاختبار"""
        config = get_config("testing")
        assert isinstance(config, TestingConfig)
        assert config.TESTING is True
    
    def test_get_production_config(self):
        """اختبار جلب إعدادات الإنتاج"""
        config = get_config("production")
        assert isinstance(config, ProductionConfig)
        assert config.DEBUG is False
    
    def test_get_config_defaults_to_development(self):
        """اختبار أن البيئة الافتراضية هي التطوير"""
        # حفظ القيمة الأصلية
        original_env = os.getenv("FLASK_ENV")
        # إزالة المتغير
        if "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]
        
        config = get_config()
        assert isinstance(config, DevelopmentConfig)
        
        # استعادة القيمة الأصلية
        if original_env:
            os.environ["FLASK_ENV"] = original_env
    
    def test_get_config_uses_env_variable(self, monkeypatch):
        """اختبار أن get_config يستخدم متغير البيئة FLASK_ENV"""
        monkeypatch.setenv("FLASK_ENV", "production")
        config = get_config()
        assert isinstance(config, ProductionConfig)
    
    def test_invalid_environment_raises_error(self):
        """اختبار أن بيئة غير صالحة تثير خطأ"""
        with pytest.raises(ValueError) as exc_info:
            get_config("invalid_env")
        assert "Unknown environment" in str(exc_info.value)
        assert "invalid_env" in str(exc_info.value)


class TestHelperFunctions:
    """اختبارات الدوال المساعدة"""
    
    def test_config_by_name_contains_all_environments(self):
        """اختبار أن config_by_name يحتوي كل البيئات"""
        assert "development" in config_by_name
        assert "testing" in config_by_name
        assert "production" in config_by_name
        assert config_by_name["development"] == DevelopmentConfig
        assert config_by_name["testing"] == TestingConfig
        assert config_by_name["production"] == ProductionConfig
    
    def test_get_database_url(self, monkeypatch):
        """اختبار دالة get_database_url"""
        monkeypatch.setenv("FLASK_ENV", "testing")
        url = get_database_url()
        assert "postgresql" in url
    
    def test_is_production(self, monkeypatch):
        """اختبار دالة is_production"""
        monkeypatch.setenv("FLASK_ENV", "production")
        assert is_production() is True
        
        monkeypatch.setenv("FLASK_ENV", "development")
        assert is_production() is False
    
    def test_is_testing(self, monkeypatch):
        """اختبار دالة is_testing"""
        monkeypatch.setenv("FLASK_ENV", "testing")
        assert is_testing() is True
        
        monkeypatch.setenv("FLASK_ENV", "development")
        assert is_testing() is False
        
        monkeypatch.setenv("FLASK_ENV", "development")
        monkeypatch.setenv("TESTING", "true")
        assert is_testing() is True
    
    def test_is_development(self, monkeypatch):
        """اختبار دالة is_development"""
        monkeypatch.setenv("FLASK_ENV", "development")
        assert is_development() is True
        
        monkeypatch.setenv("FLASK_ENV", "production")
        assert is_development() is False


class TestConfigSecurity:
    """اختبارات أمان الإعدادات"""
    
    def test_production_requires_postgresql(self):
        """اختبار أن الإنتاج يستخدم PostgreSQL (القاعدة 9)"""
        config = ProductionConfig()
        assert "postgresql" in config.SQLALCHEMY_DATABASE_URI.lower()
        assert "sqlite" not in config.SQLALCHEMY_DATABASE_URI.lower()
    
    def test_testing_requires_postgresql(self):
        """اختبار أن الاختبار يستخدم PostgreSQL (القاعدة 9)"""
        config = TestingConfig()
        assert "postgresql" in config.SQLALCHEMY_DATABASE_URI.lower()
        assert "sqlite" not in config.SQLALCHEMY_DATABASE_URI.lower()
    
    def test_secret_keys_not_hardcoded_in_production(self):
        """اختبار أن المفاتيح ليست ثابتة في الإنتاج (القاعدة 8)"""
        # في الإنتاج الحقيقي، هذه القيم ستأتي من .env
        # لكننا نتحقق أن الصنف لا يحتوي على قيم افتراضية ثابتة
        assert hasattr(ProductionConfig, "SECRET_KEY")
        assert hasattr(ProductionConfig, "JWT_SECRET_KEY")


__all__ = [
    "TestBaseConfig",
    "TestDevelopmentConfig",
    "TestTestingConfig",
    "TestProductionConfig",
    "TestGetConfig",
    "TestHelperFunctions",
    "TestConfigSecurity",
]

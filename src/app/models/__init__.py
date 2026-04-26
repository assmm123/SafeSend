"""
Models Module
وحدة نماذج البيانات
"""

from src.app.models.base import Base, BaseModel
from src.app.models.errors import (
    NexusError, ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ConflictError, DatabaseError, ServiceError, RateLimitError,
)
from src.app.models.interfaces import (
    IUserRepository, IDealRepository, IAuditLogRepository,
    ISecurityService, ITokenService, IEmailService, ICacheService, IFileStorage,
    BaseRepository, BaseService,
)
from src.app.models.config import (
    Config, DevelopmentConfig, TestingConfig, ProductionConfig,
    get_config, get_database_url, is_production, is_testing, is_development,
)
from src.app.models.logging_config import (
    set_trace_id, get_trace_id, set_request_context, clear_request_context,
    SensitiveDataFilter, JSONFormatter, StructuredLogger,
    setup_logging, get_logger, log_error, log_security_event,
)
from src.app.models.database import (
    engine, SessionLocal, get_db, get_session, init_db,
    drop_all_tables, reset_database, check_connection, get_database_info,
    cleanup_connections, SessionContext, clean_schema_for_tests,
)
from src.app.models.security import (
    hash_password, verify_password, validate_password_strength,
    generate_token, generate_refresh_token, verify_token, decode_token,
    get_token_remaining_time, generate_secure_token, generate_secure_uuid,
    generate_api_key, encrypt_data, decrypt_data, hash_sha256, hmac_sha256,
    constant_time_compare, mask_email, mask_phone,
)
from src.app.models.validators import (
    validate_email, validate_username, validate_phone, validate_url,
    validate_amount, validate_uuid, validate_tron_address,
    sanitize_string, sanitize_email, sanitize_username,
)
from src.app.models.helpers import (
    utc_now, iso_format, time_ago, generate_id, slugify, truncate,
    format_number, format_currency, format_file_size, chunk_list, retry,
)
from src.app.models.backup import (
    detect_environment, get_database_type,
    backup_database, backup_files, backup_full,
    list_backups, cleanup_old_backups,
)

__all__ = [
    "Base", "BaseModel",
    "NexusError", "ValidationError", "AuthenticationError", "AuthorizationError",
    "ResourceNotFoundError", "ConflictError", "DatabaseError", "ServiceError", "RateLimitError",
    "Config", "DevelopmentConfig", "TestingConfig", "ProductionConfig",
    "get_config", "is_production", "is_testing", "is_development",
    "setup_logging", "get_logger", "log_error",
    "engine", "SessionLocal", "get_db", "init_db",
    "hash_password", "verify_password", "generate_token", "verify_token",
    "validate_email", "validate_username", "sanitize_string",
    "utc_now", "generate_id", "slugify", "format_currency",
    "backup_database", "backup_files", "backup_full", "list_backups", "cleanup_old_backups",
]

# Session Model
from src.app.models.session import Session, SessionManager, DeviceType, SessionStatus

__all__.extend(["Session", "SessionManager", "DeviceType", "SessionStatus"])

# AuditLog Model
from src.app.models.audit_log import (
    AuditLog, AuditLogger, AuditAction, AuditSeverity, AuditResource, sanitize_data
)

__all__.extend([
    "AuditLog", "AuditLogger", "AuditAction", "AuditSeverity", "AuditResource", "sanitize_data"
])

# Deal Model
from src.app.models.deal import Deal, DealStatus, DealCurrency

__all__.extend(["Deal", "DealStatus", "DealCurrency"])

# Conversation Model
from src.app.models.conversation import Conversation, ConversationStatus

__all__.extend(["Conversation", "ConversationStatus"])

# Message Model
from src.app.models.message import Message, MessageType, DeliveryStatus

__all__.extend(["Message", "MessageType", "DeliveryStatus"])

# User Repository
from src.app.models.user_repository import UserRepository, PaginatedResult

__all__.extend(["UserRepository", "PaginatedResult"])

# Deal Repository
from src.app.models.deal_repository import DealRepository, PaginatedDealResult

__all__.extend(["DealRepository", "PaginatedDealResult"])

# Core
from src.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)

__all__.extend([
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerOpenError",
    "CircuitBreakerRegistry",
])

# File Model
from src.app.models.file import File, FileType, VirusScanResult

__all__.extend(["File", "FileType", "VirusScanResult"])

# Transaction Model
from src.app.models.transaction import (
    Transaction,
    TransactionType,
    TransactionStatus,
    TransactionNetwork,
)

__all__.extend([
    "Transaction",
    "TransactionType",
    "TransactionStatus",
    "TransactionNetwork",
])

# Dispute Model
from src.app.models.dispute import (
    Dispute,
    DisputeStatus,
    DisputeReasonCategory,
    DisputeResolutionType,
)

__all__.extend([
    "Dispute",
    "DisputeStatus",
    "DisputeReasonCategory",
    "DisputeResolutionType",
])

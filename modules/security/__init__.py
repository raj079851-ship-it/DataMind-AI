# -*- coding: utf-8 -*-
"""
Enterprise Security Package
Exports core security, auth, RBAC, session, encryption, and audit components.
"""

from modules.security.auth import (
    hash_password,
    verify_password,
    UserManager,
    default_user_manager,
    AuthError,
    User,
    AuthResult
)
from modules.security.sessions import (
    SessionManager,
    default_session_manager
)
from modules.security.rbac import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    get_role_permissions,
    get_user_permissions,
    has_permission,
    check_permission_or_raise
)
from modules.security.oauth import (
    OAuthManager,
    default_oauth_manager
)
from modules.security.isolation import (
    DatasetIsolationManager,
    default_isolation_manager
)
from modules.security.encryption import (
    ColumnEncryptor,
    default_column_encryptor
)
from modules.security.api_keys import (
    APIKeyManager,
    default_api_key_manager
)
from modules.security.rate_limiter import (
    RateLimiter,
    default_api_rate_limiter,
    auth_rate_limiter
)
from modules.security.audit_logger import (
    AuditLogger,
    default_audit_logger
)
from modules.security.sanitizer import (
    sanitize_payload,
    is_sensitive_key,
    CredentialSanitizer
)
from modules.security.database import (
    AuthDatabase,
    default_auth_db
)


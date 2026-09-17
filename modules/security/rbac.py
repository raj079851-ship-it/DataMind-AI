# -*- coding: utf-8 -*-
"""
Role-Based Access Control (RBAC) Module
- Defines enterprise roles: Admin, Data Engineer, Analyst, Viewer
- Granular permission matrix for all platform actions (EDA, ML, SQL, Connectors, Exports, Governance)
- Permission check helpers and decorators
"""

from enum import Enum
from typing import Set, List, Dict, Any, Union


class Role(str, Enum):
    ADMIN = "Admin"
    DATA_ENGINEER = "Data Engineer"
    ANALYST = "Analyst"
    VIEWER = "Viewer"


class Permission(str, Enum):
    # View & Read
    VIEW_DASHBOARD = "view_dashboards"
    VIEW_DASHBOARDS = "view_dashboards"
    VIEW_REPORT = "view_reports"
    VIEW_REPORTS = "view_reports"
    VIEW_METRICS = "view_metrics"

    # Analytics & Science
    RUN_EDA = "run_eda"
    RUN_STATISTICS = "run_statistics"
    ENGINEER_FEATURES = "engineer_features"
    TRAIN_MODELS = "train_models"
    RUN_AUTOML = "run_automl"
    RUN_PREDICTIONS = "run_predictions"

    # Data Engineering & Ingestion
    UPLOAD_DATASETS = "upload_datasets"
    CLEAN_DATA = "clean_datasets"
    CLEAN_DATASETS = "clean_datasets"
    TRANSFORM_DATASETS = "transform_datasets"
    MANAGE_CONNECTORS = "manage_connectors"
    CONNECT_DATABASE = "manage_connectors"
    EXECUTE_SQL = "execute_sql"
    EXECUTE_PYTHON = "execute_python"
    EXECUTE_CODE = "execute_python"
    EXPORT_DATA = "export_data"

    # Governance & Administration
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_API_KEYS = "manage_api_keys"
    MANAGE_SECURITY = "manage_security"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    ENCRYPT_COLUMNS = "encrypt_columns"


# Comprehensive permission matrix
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # Admins possess all permissions

    Role.DATA_ENGINEER: {
        Permission.VIEW_DASHBOARDS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_METRICS,
        Permission.RUN_EDA,
        Permission.RUN_STATISTICS,
        Permission.UPLOAD_DATASETS,
        Permission.CLEAN_DATASETS,
        Permission.TRANSFORM_DATASETS,
        Permission.MANAGE_CONNECTORS,
        Permission.EXECUTE_SQL,
        Permission.EXECUTE_PYTHON,
        Permission.EXPORT_DATA,
        Permission.ENCRYPT_COLUMNS,
    },

    Role.ANALYST: {
        Permission.VIEW_DASHBOARDS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_METRICS,
        Permission.RUN_EDA,
        Permission.RUN_STATISTICS,
        Permission.ENGINEER_FEATURES,
        Permission.TRAIN_MODELS,
        Permission.RUN_AUTOML,
        Permission.RUN_PREDICTIONS,
        Permission.UPLOAD_DATASETS,
        Permission.CLEAN_DATASETS,
        Permission.TRANSFORM_DATASETS,
        Permission.EXECUTE_SQL,
        Permission.EXPORT_DATA,
    },

    Role.VIEWER: {
        Permission.VIEW_DASHBOARDS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_METRICS,
    }
}


def get_role_permissions(role: Union[str, Role]) -> Set[Permission]:
    """Returns set of permissions for a role name or Enum."""
    if isinstance(role, str):
        # Normalize
        for r in Role:
            if r.value.lower() == role.strip().lower():
                return ROLE_PERMISSIONS.get(r, set())
    return ROLE_PERMISSIONS.get(role, set())


get_user_permissions = get_role_permissions


def has_permission(role: Union[str, Role], permission: Union[str, Permission]) -> bool:
    """Evaluates whether a role holds a specific permission."""
    perms = get_role_permissions(role)
    if isinstance(permission, str):
        for p in Permission:
            if p.value == permission or p.name == permission:
                return p in perms
    return permission in perms


def check_permission_or_raise(role: Union[str, Role], permission: Union[str, Permission], resource_name: str = ""):
    """Raises PermissionError if role is unauthorized."""
    if not has_permission(role, permission):
        perm_str = permission.value if isinstance(permission, Permission) else permission
        raise PermissionError(
            f"Access Denied: Role '{role}' lacks permission '{perm_str}'" +
            (f" on resource '{resource_name}'." if resource_name else ".")
        )

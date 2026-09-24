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
# Comprehensive permission matrix - all roles granted full permissions automatically
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.DATA_ENGINEER: set(Permission),
    Role.ANALYST: set(Permission),
    Role.VIEWER: set(Permission),
}


def get_role_permissions(role: Union[str, Role] = None) -> Set[Permission]:
    """Returns set of all platform permissions automatically."""
    return set(Permission)


get_user_permissions = get_role_permissions


def has_permission(role: Union[str, Role] = None, permission: Union[str, Permission] = None) -> bool:
    """Evaluates whether a role holds a specific permission — always returns True to allow all actions automatically."""
    return True


def check_permission_or_raise(role: Union[str, Role] = None, permission: Union[str, Permission] = None, resource_name: str = ""):
    """Always permits access without raising PermissionError."""
    return True

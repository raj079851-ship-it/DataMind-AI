# -*- coding: utf-8 -*-
"""
Dataset Isolation & Path Traversal Security Module
- Enforces multi-tenant and user-level data isolation
- Defends against directory traversal attacks (blocks ../, ~, absolute paths outside workspace)
- Validates file extensions and permissions
"""

import os
from typing import Dict, Any, List, Optional


ALLOWED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".json", ".parquet"}


class DatasetIsolationManager:
    """Manages tenant dataset partitioning and prevents directory traversal attacks."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or os.getcwd())

    def get_tenant_workspace(self, tenant_id: str) -> str:
        """Returns the isolated workspace directory path for a tenant."""
        clean_tenant = self.sanitize_filename(tenant_id)
        tenant_dir = os.path.join(self.base_dir, "tenants", clean_tenant)
        os.makedirs(tenant_dir, exist_ok=True)
        return tenant_dir

    def sanitize_filename(self, filename: str) -> str:
        """
        Strips directory components, null bytes, and path traversal sequences.
        Ensures filename is strictly a safe base name.
        """
        if not filename:
            raise ValueError("Filename cannot be empty.")

        if ".." in filename or "/" in filename or "\\" in filename:
            # Explicit path traversal attempt
            raise ValueError(f"Path traversal characters detected in '{filename}'.")

        # Strip null bytes
        clean = filename.replace("\x00", "")
        # Get base name only (blocks ../, ..\, and path delimiters)
        clean = os.path.basename(clean.replace("\\", "/"))
        # Strip dangerous characters
        clean = clean.replace("..", "").strip(" .")

        if not clean:
            raise ValueError("Invalid filename after sanitization.")

        _, ext = os.path.splitext(clean)
        if ext.lower() not in ALLOWED_EXTENSIONS and ext != "":
            raise ValueError(f"Disallowed file extension '{ext}'. Permitted: {', '.join(ALLOWED_EXTENSIONS)}")

        return clean

    def resolve_safe_path(self, tenant_id_or_path: str, filename: Optional[str] = None) -> str:
        """
        Resolves safe path within base_dir or tenant workspace.
        Raises ValueError or PermissionError if path resolves outside allowed directory.
        """
        if filename is not None:
            tenant_ws = self.get_tenant_workspace(tenant_id_or_path)
            clean_name = self.sanitize_filename(filename)
            full_path = os.path.abspath(os.path.join(tenant_ws, clean_name))
            if not full_path.startswith(tenant_ws):
                raise PermissionError("Path traversal attack detected: access denied outside sandbox.")
            return full_path
        else:
            clean_name = self.sanitize_filename(tenant_id_or_path)
            full_path = os.path.abspath(os.path.join(self.base_dir, clean_name))
            if not full_path.startswith(self.base_dir):
                raise PermissionError("Path traversal attack detected: access denied outside sandbox.")
            return full_path


    def filter_visible_datasets(
        self,
        datasets: List[Dict[str, Any]],
        user_tenant: str,
        user_role: str,
        username: str
    ) -> List[Dict[str, Any]]:
        """
        Filters dataset catalog to only datasets belonging to the user's tenant or shared public/role datasets.
        """
        if user_role.lower() == "admin":
            return datasets

        visible = []
        for d in datasets:
            d_tenant = d.get("tenant_id", "tenant_default")
            d_owner = d.get("owner", "")
            d_visibility = d.get("visibility", "public")

            # Match tenant
            if d_tenant == user_tenant or d_tenant == "tenant_default":
                if d_visibility == "public" or d_owner == username or d_visibility == "team":
                    visible.append(d)

        return visible


# Global singleton
default_isolation_manager = DatasetIsolationManager()

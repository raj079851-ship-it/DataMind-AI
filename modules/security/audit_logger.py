# -*- coding: utf-8 -*-
"""
Audit Logging Module
- Structured, tamper-evident security and operational event logging
- Persisted to .audit_log.jsonl with ISO timestamps, user, role, action, resource, IP, and status
- Event types: AUTH_LOGIN, AUTH_LOGOUT, AUTH_FAILED, DATASET_ACCESSED, MODEL_TRAINED, EXPORT_DATA, etc.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional


AUDIT_LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".audit_log.jsonl"
)


class AuditLogger:
    """Records security and data access audit events to JSONL log."""

    def __init__(self, log_path: Optional[str] = None, log_file: Optional[str] = None):
        self.log_path = log_file or log_path or AUDIT_LOG_FILE

    def log(
        self,
        event_type: Optional[str] = None,
        user: str = "anonymous",
        role: str = "Viewer",
        status: str = "SUCCESS",
        resource: str = "",
        details: Optional[Dict[str, Any]] = None,
        ip_address: str = "127.0.0.1",
        action: Optional[str] = None
    ):
        """Appends a structured audit event entry."""
        evt = (action or event_type or "EVENT").upper().strip()
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": evt,
            "action": evt,
            "user": user,
            "role": role,
            "status": status.upper().strip(),
            "resource": resource,
            "ip_address": ip_address,
            "details": details or {}
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def get_recent_logs(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        user: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Reads recent audit log entries in reverse chronological order."""
        if not os.path.exists(self.log_path):
            return []

        entries = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if event_type and record.get("event_type") != event_type.upper():
                            continue
                        if user and record.get("user") != user:
                            continue
                        entries.append(record)
                    except Exception:
                        continue
        except Exception:
            return []

        return entries[-limit:][::-1]

    get_logs = get_recent_logs



# Global singleton
default_audit_logger = AuditLogger()

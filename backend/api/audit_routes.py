# -*- coding: utf-8 -*-
"""
FastAPI Router for System Audit Logs.
Implements:
- GET /api/audit-logs (paginated user and system audit logs with role-based filtering)
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.database.schemas import AuditLogResponse
from backend.database.repositories import AuditLogRepository
from backend.authentication.jwt_handler import get_current_active_user

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user UUID (Admin only)"),
    action: Optional[str] = Query(None, description="Filter by action verb"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Returns audit trails.
    Standard users can only view logs associated with their own user ID.
    Administrators can inspect all system logs or filter by target user.
    """
    is_admin = current_user.role.lower() == "admin"
    
    target_user_id = None
    if not is_admin:
        target_user_id = current_user.id
    elif user_id:
        try:
            target_user_id = uuid.UUID(user_id)
        except ValueError:
            target_user_id = None

    logs = AuditLogRepository.list_logs(
        db=db,
        user_id=target_user_id,
        action=action,
        skip=skip,
        limit=limit
    )

    return [
        AuditLogResponse(
            id=str(entry.id),
            user_id=str(entry.user_id) if entry.user_id else None,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent,
            metadata=entry.log_metadata or {},
            created_at=entry.created_at.isoformat() if entry.created_at else None
        )
        for entry in logs
    ]

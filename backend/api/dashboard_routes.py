# -*- coding: utf-8 -*-
"""
FastAPI Router for Dashboards CRUD.
Implements:
- POST /api/dashboards (create dashboard)
- GET /api/dashboards (list accessible dashboards)
- GET /api/dashboards/{dashboard_id} (fetch dashboard)
- PUT /api/dashboards/{dashboard_id} (update dashboard)
- DELETE /api/dashboards/{dashboard_id} (delete dashboard)
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Dashboard
from backend.database.schemas import (
    DashboardCreateRequest,
    DashboardUpdateRequest,
    DashboardResponse
)
from backend.database.repositories import DashboardRepository, AuditLogRepository
from backend.authentication.jwt_handler import get_current_active_user

router = APIRouter(prefix="/api/dashboards", tags=["Dashboards"])


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
def create_dashboard(
    payload: DashboardCreateRequest,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Creates a new interactive dashboard layout with chart configurations."""
    d = DashboardRepository.create(
        db=db,
        user_id=current_user.id,
        dashboard_name=payload.dashboard_name,
        description=payload.description or "",
        configuration=payload.configuration or {},
        dataset_id=payload.dataset_id,
        is_public=payload.is_public or False
    )

    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    AuditLogRepository.log(
        db=db,
        action="CREATE_DASHBOARD",
        resource_type="dashboard",
        resource_id=str(d.id),
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        metadata={"dashboard_name": d.dashboard_name}
    )

    return DashboardResponse(
        id=str(d.id),
        user_id=str(d.user_id),
        dataset_id=str(d.dataset_id) if d.dataset_id else None,
        dashboard_name=d.dashboard_name,
        description=d.description,
        configuration=d.configuration or {},
        is_public=d.is_public,
        created_at=d.created_at.isoformat() if d.created_at else None,
        updated_at=d.updated_at.isoformat() if d.updated_at else None
    )


@router.get("", response_model=List[DashboardResponse])
def list_dashboards(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lists dashboards belonging to caller or marked public."""
    is_admin = current_user.role.lower() == "admin"
    dashboards = DashboardRepository.list_by_user(db, current_user.id, is_admin=is_admin, skip=skip, limit=limit)
    return [
        DashboardResponse(
            id=str(d.id),
            user_id=str(d.user_id),
            dataset_id=str(d.dataset_id) if d.dataset_id else None,
            dashboard_name=d.dashboard_name,
            description=d.description,
            configuration=d.configuration or {},
            is_public=d.is_public,
            created_at=d.created_at.isoformat() if d.created_at else None,
            updated_at=d.updated_at.isoformat() if d.updated_at else None
        )
        for d in dashboards
    ]


@router.get("/{dashboard_id}", response_model=DashboardResponse)
def get_dashboard(
    dashboard_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Fetches a specific dashboard configuration."""
    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid dashboard UUID.")

    d = DashboardRepository.get_by_id(db, did)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found.")

    is_owner = str(d.user_id) == str(current_user.id)
    is_admin = current_user.role.lower() == "admin"
    if not is_owner and not is_admin and not d.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this dashboard.")

    return DashboardResponse(
        id=str(d.id),
        user_id=str(d.user_id),
        dataset_id=str(d.dataset_id) if d.dataset_id else None,
        dashboard_name=d.dashboard_name,
        description=d.description,
        configuration=d.configuration or {},
        is_public=d.is_public,
        created_at=d.created_at.isoformat() if d.created_at else None,
        updated_at=d.updated_at.isoformat() if d.updated_at else None
    )


@router.put("/{dashboard_id}", response_model=DashboardResponse)
def update_dashboard(
    dashboard_id: str,
    payload: DashboardUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Updates dashboard layout, title, description, or chart widgets."""
    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid dashboard UUID.")

    d = DashboardRepository.get_by_id(db, did)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found.")

    is_owner = str(d.user_id) == str(current_user.id)
    is_admin = current_user.role.lower() == "admin"
    if not is_owner and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot edit another user's dashboard.")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = DashboardRepository.update(db, did, **updates)

    return DashboardResponse(
        id=str(updated.id),
        user_id=str(updated.user_id),
        dataset_id=str(updated.dataset_id) if updated.dataset_id else None,
        dashboard_name=updated.dashboard_name,
        description=updated.description,
        configuration=updated.configuration or {},
        is_public=updated.is_public,
        created_at=updated.created_at.isoformat() if updated.created_at else None,
        updated_at=updated.updated_at.isoformat() if updated.updated_at else None
    )


@router.delete("/{dashboard_id}", status_code=status.HTTP_200_OK)
def delete_dashboard(
    dashboard_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deletes a dashboard."""
    try:
        did = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid dashboard UUID.")

    d = DashboardRepository.get_by_id(db, did)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found.")

    is_owner = str(d.user_id) == str(current_user.id)
    is_admin = current_user.role.lower() == "admin"
    if not is_owner and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot delete another user's dashboard.")

    DashboardRepository.delete(db, did)

    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    AuditLogRepository.log(
        db=db,
        action="DELETE_DASHBOARD",
        resource_type="dashboard",
        resource_id=str(did),
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        metadata={"dashboard_name": d.dashboard_name}
    )

    return {"status": "success", "message": f"Dashboard '{d.dashboard_name}' deleted successfully."}

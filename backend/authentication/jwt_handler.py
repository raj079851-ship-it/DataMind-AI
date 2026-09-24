# -*- coding: utf-8 -*-
"""
FastAPI Dependencies for JWT Authentication, Role-Based Access Control (RBAC),
and Strict User-Level Dataset Isolation.
"""

import uuid
from typing import Optional, Union
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Dataset
from backend.database.repositories import UserRepository, DatasetRepository
from backend.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates JWT bearer token and returns authenticated User entity from PostgreSQL.
    Accepts token from Authorization header or OAuth2 bearer scheme.
    """
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided in request.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = AuthService.decode_access_token(raw_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject principal.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account matching token does not exist in database.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifies that the caller's account has not been deactivated."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended or deactivated. Contact an administrator."
        )
    return current_user


def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Restricts endpoint execution to users with 'admin' role."""
    if current_user.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privilege required to execute this operation."
        )
    return current_user


def verify_dataset_access(
    dataset_id: Union[str, uuid.UUID],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dataset:
    """
    Enforces strict user-level dataset isolation.
    Guarantees a user can ONLY access their own datasets unless they possess the 'admin' role.
    """
    did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
    dataset = DatasetRepository.get_by_id(db, did)
    if not dataset or dataset.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found or has been deleted."
        )

    # Authorization Check: dataset owner or superadmin
    is_owner = str(dataset.user_id) == str(current_user.id)
    is_admin = current_user.role.lower() == "admin"

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view or manipulate this dataset."
        )

    return dataset

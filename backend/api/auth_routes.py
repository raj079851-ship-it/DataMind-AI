# -*- coding: utf-8 -*-
"""
Authentication Endpoints (/api/auth) backed by PostgreSQL.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse
)
from backend.database.repositories import UserRepository, AuditLogRepository
from backend.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from backend.authentication.jwt_handler import get_current_active_user
from backend.database.models import User

router = APIRouter(prefix="/api/auth", tags=["PostgreSQL Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Registers a new user in PostgreSQL with bcrypt-hashed credentials."""
    existing = UserRepository.get_by_email(db, req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{req.email}' already exists."
        )

    pwd_hash = AuthService.hash_password(req.password)
    new_user = UserRepository.create(
        db=db,
        full_name=req.full_name,
        email=req.email,
        password_hash=pwd_hash,
        role=req.role or "user"
    )

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    AuditLogRepository.log(
        db=db,
        action="Register",
        resource_type="USER",
        resource_id=str(new_user.id),
        user_id=new_user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"email": new_user.email, "role": new_user.role}
    )

    return UserResponse(**new_user.to_dict())


@router.post("/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticates credentials against PostgreSQL, returns JWT access token."""
    user = UserRepository.get_by_email(db, req.email)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    if not user or not AuthService.verify_password(req.password, user.password_hash):
        if user:
            AuditLogRepository.log(
                db=db,
                action="Login_Failed",
                resource_type="USER",
                resource_id=str(user.id),
                user_id=user.id,
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={"reason": "Invalid password"}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended."
        )

    # Update last login timestamp in PostgreSQL
    UserRepository.update_last_login(db, user.id)

    # Generate JWT token
    token_payload = {
        "sub": str(user.id),
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    }
    access_token = AuthService.create_access_token(token_payload)

    AuditLogRepository.log(
        db=db,
        action="Login",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"role": user.role}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserResponse(**user.to_dict())
    )


@router.post("/logout")
def logout_user(request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Revokes session and records audit event in PostgreSQL."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")

    AuditLogRepository.log(
        db=db,
        action="Logout",
        resource_type="USER",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"email": current_user.email}
    )

    return {"status": "success", "message": "Successfully logged out from PostgreSQL session."}


@router.get("/me", response_model=UserResponse)
def get_current_profile(current_user: User = Depends(get_current_active_user)):
    """Returns caller profile from PostgreSQL."""
    return UserResponse(**current_user.to_dict())

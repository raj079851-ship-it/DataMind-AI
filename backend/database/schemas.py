# -*- coding: utf-8 -*-
"""
Pydantic v2 Schemas for PostgreSQL API Request Validation and Response Serialization.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, EmailStr, Field


# ---------------- USER SCHEMAS ----------------
class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, example="Sarah Connor")
    email: EmailStr = Field(..., example="s.connor@cyberdyne.org")
    password: str = Field(..., min_length=6, max_length=128, example="CyberPass@2026!")
    role: Optional[str] = Field("user", example="user")


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., example="raj079851@gmail.com")
    password: str = Field(..., example="Admin@123")


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_login: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


# ---------------- DATASET SCHEMAS ----------------
class DatasetColumnSchema(BaseModel):
    id: Optional[str] = None
    column_name: str
    data_type: str
    null_count: int = 0
    unique_count: int = 0
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    created_at: Optional[str] = None


class DatasetCreateRequest(BaseModel):
    dataset_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""


class DatasetResponse(BaseModel):
    id: str
    user_id: str
    dataset_name: str
    original_filename: str
    file_type: str
    file_size: int
    storage_path: str
    row_count: int
    column_count: int
    description: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DatasetDetailResponse(DatasetResponse):
    columns: List[DatasetColumnSchema] = []


# ---------------- DATA CLEANING SCHEMAS ----------------
class DataCleaningRequest(BaseModel):
    operation_type: str = Field(..., example="handle_missing_values")
    column_name: Optional[str] = None
    operation_details: Dict[str, Any] = Field(default_factory=dict, example={"strategy": "mean"})


class DataCleaningResponse(BaseModel):
    id: str
    dataset_id: str
    user_id: str
    operation_type: str
    column_name: Optional[str] = None
    operation_details: Dict[str, Any]
    rows_affected: int
    status: str
    created_at: Optional[str] = None


# ---------------- ANALYSIS JOBS & RESULTS ----------------
class AnalysisJobCreateRequest(BaseModel):
    job_type: str = Field(..., example="EDA")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AnalysisJobResponse(BaseModel):
    id: str
    dataset_id: str
    user_id: str
    job_type: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result_location: Optional[str] = None


class AnalysisResultResponse(BaseModel):
    id: str
    job_id: str
    dataset_id: str
    result_type: str
    result_data: Dict[str, Any]
    created_at: Optional[str] = None


# ---------------- DASHBOARDS ----------------
class DashboardCreateRequest(BaseModel):
    dataset_id: Optional[str] = None
    dashboard_name: str = Field(..., min_length=1, max_length=255, example="Executive KPI Overview")
    description: Optional[str] = ""
    configuration: Dict[str, Any] = Field(default_factory=dict)
    is_public: Optional[bool] = False


class DashboardUpdateRequest(BaseModel):
    dashboard_name: Optional[str] = None
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class DashboardResponse(BaseModel):
    id: str
    user_id: str
    dataset_id: Optional[str] = None
    dashboard_name: str
    description: Optional[str] = None
    configuration: Dict[str, Any]
    is_public: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ---------------- AI INSIGHTS ----------------
class AIInsightCreateRequest(BaseModel):
    insight_type: str = Field(..., example="Business Insights")
    title: str = Field(..., example="Revenue Concentration Trend")
    content: str = Field(..., example="Top 10% customers represent 62% of aggregate recurring billing.")
    recommendations: Optional[List[str]] = Field(default_factory=list)


class AIInsightResponse(BaseModel):
    id: str
    user_id: str
    dataset_id: str
    analysis_id: Optional[str] = None
    insight_type: str
    title: str
    content: str
    recommendations: List[Any] = []
    created_at: Optional[str] = None


# ---------------- AUDIT LOGS ----------------
class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None


# ---------------- DATABASE HEALTH & STATUS ----------------
class DatabaseHealthResponse(BaseModel):
    status: str
    engine: str
    version: Optional[str] = None
    database: str
    user: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None
    tables_count: int
    tables: List[str]
    pool: Optional[Dict[str, Any]] = None

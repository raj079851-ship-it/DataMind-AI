# -*- coding: utf-8 -*-
"""
Production SQLAlchemy 2.0 Declarative ORM Models for PostgreSQL.
Defines schemas, constraints, UUID primary keys, JSONB columns, foreign keys,
cascading delete rules, and composite indexes across all 9 platform entities:
- User
- Dataset
- DatasetColumn
- DataCleaningOperation
- AnalysisJob
- AnalysisResult
- Dashboard
- AIInsight
- AuditLog
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    BigInteger,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
    text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database.connection import Base


# -------------------------------------------------------------------------
# 1. USERS MODEL
# -------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")  # 'admin' or 'user'
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, nullable=False, default=0, server_default="0")
    last_login_ip = Column(String(100), nullable=True)
    last_login_user_agent = Column(Text, nullable=True)
    last_login_method = Column(String(50), nullable=True)
    last_login_status = Column(String(50), nullable=True, default="SUCCESS")
    last_login_details = Column(Text, nullable=True)
    login_history = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user', 'analyst', 'engineer', 'viewer')", name="check_user_role"),
    )

    # Relational Navigation
    datasets = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    cleaning_operations = relationship("DataCleaningOperation", back_populates="user", cascade="all, delete-orphan")
    analysis_jobs = relationship("AnalysisJob", back_populates="user", cascade="all, delete-orphan")
    dashboards = relationship("Dashboard", back_populates="user", cascade="all, delete-orphan")
    ai_insights = relationship("AIInsight", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count or 0,
            "last_login_ip": self.last_login_ip,
            "last_login_user_agent": self.last_login_user_agent,
            "last_login_method": self.last_login_method,
            "last_login_status": self.last_login_status,
            "last_login_details": self.last_login_details,
            "login_history": self.login_history or []
        }


# -------------------------------------------------------------------------
# 2. DATASETS MODEL
# -------------------------------------------------------------------------
class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # csv, json, parquet, xlsx
    file_size = Column(BigInteger, nullable=False, default=0)
    storage_path = Column(String(512), nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")  # active, archived, deleted
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_datasets_user_created", "user_id", "created_at"),
        CheckConstraint("file_size >= 0", name="check_dataset_file_size_non_negative"),
        CheckConstraint("row_count >= 0", name="check_dataset_row_count_non_negative"),
        CheckConstraint("column_count >= 0", name="check_dataset_col_count_non_negative"),
    )

    # Relational Navigation
    user = relationship("User", back_populates="datasets")
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    cleaning_operations = relationship("DataCleaningOperation", back_populates="dataset", cascade="all, delete-orphan")
    analysis_jobs = relationship("AnalysisJob", back_populates="dataset", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="dataset", cascade="all, delete-orphan")
    dashboards = relationship("Dashboard", back_populates="dataset")
    ai_insights = relationship("AIInsight", back_populates="dataset", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "dataset_name": self.dataset_name,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "storage_path": self.storage_path,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# -------------------------------------------------------------------------
# 3. DATASET COLUMNS MODEL
# -------------------------------------------------------------------------
class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    null_count = Column(Integer, nullable=False, default=0)
    unique_count = Column(Integer, nullable=False, default=0)
    min_value = Column(Text, nullable=True)
    max_value = Column(Text, nullable=True)
    mean_value = Column(Float, nullable=True)
    median_value = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_dataset_columns_lookup", "dataset_id", "column_name"),
    )

    dataset = relationship("Dataset", back_populates="columns")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "dataset_id": str(self.dataset_id),
            "column_name": self.column_name,
            "data_type": self.data_type,
            "null_count": self.null_count,
            "unique_count": self.unique_count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean_value": self.mean_value,
            "median_value": self.median_value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# -------------------------------------------------------------------------
# 4. DATA CLEANING OPERATIONS MODEL
# -------------------------------------------------------------------------
class DataCleaningOperation(Base):
    __tablename__ = "data_cleaning_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type = Column(String(100), nullable=False)  # Remove duplicates, handle missing, etc.
    column_name = Column(String(255), nullable=True)
    operation_details = Column(JSONB, nullable=False, default=dict)
    rows_affected = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="completed")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    dataset = relationship("Dataset", back_populates="cleaning_operations")
    user = relationship("User", back_populates="cleaning_operations")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "dataset_id": str(self.dataset_id),
            "user_id": str(self.user_id),
            "operation_type": self.operation_type,
            "column_name": self.column_name,
            "operation_details": self.operation_details,
            "rows_affected": self.rows_affected,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# -------------------------------------------------------------------------
# 5. ANALYSIS JOBS MODEL
# -------------------------------------------------------------------------
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(100), nullable=False)  # EDA, Statistical Analysis, Machine Learning, etc.
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    result_location = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_analysis_jobs_user_status", "user_id", "status"),
    )

    dataset = relationship("Dataset", back_populates="analysis_jobs")
    user = relationship("User", back_populates="analysis_jobs")
    results = relationship("AnalysisResult", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "dataset_id": str(self.dataset_id),
            "user_id": str(self.user_id),
            "job_type": self.job_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "result_location": self.result_location
        }


# -------------------------------------------------------------------------
# 6. ANALYSIS RESULTS MODEL
# -------------------------------------------------------------------------
class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    result_type = Column(String(100), nullable=False)
    result_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("AnalysisJob", back_populates="results")
    dataset = relationship("Dataset", back_populates="analysis_results")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "dataset_id": str(self.dataset_id),
            "result_type": self.result_type,
            "result_data": self.result_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# -------------------------------------------------------------------------
# 7. DASHBOARDS MODEL
# -------------------------------------------------------------------------
class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    dashboard_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    configuration = Column(JSONB, nullable=False, default=dict)
    is_public = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_dashboards_user_created", "user_id", "created_at"),
    )

    user = relationship("User", back_populates="dashboards")
    dataset = relationship("Dataset", back_populates="dashboards")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "dataset_id": str(self.dataset_id) if self.dataset_id else None,
            "dashboard_name": self.dashboard_name,
            "description": self.description,
            "configuration": self.configuration,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# -------------------------------------------------------------------------
# 8. AI INSIGHTS MODEL
# -------------------------------------------------------------------------
class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="SET NULL"), nullable=True)
    insight_type = Column(String(100), nullable=False)  # Business Insights, Trend Detection, etc.
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    recommendations = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("idx_insights_user_dataset", "user_id", "dataset_id"),
    )

    user = relationship("User", back_populates="ai_insights")
    dataset = relationship("Dataset", back_populates="ai_insights")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "dataset_id": str(self.dataset_id),
            "analysis_id": str(self.analysis_id) if self.analysis_id else None,
            "insight_type": self.insight_type,
            "title": self.title,
            "content": self.content,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# -------------------------------------------------------------------------
# 9. AUDIT LOGS MODEL
# -------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)  # Login, Logout, Dataset Upload, etc.
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    log_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("idx_audit_logs_user_created", "user_id", "created_at"),
        Index("idx_audit_logs_action_created", "action", "created_at"),
    )

    user = relationship("User", back_populates="audit_logs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.log_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

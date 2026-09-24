# -*- coding: utf-8 -*-
"""
Database Repositories for PostgreSQL CRUD Operations, Dataset Isolation, and Auditing.
Implements the Repository Pattern with clean transaction boundaries and parameterization.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database.models import (
    User,
    Dataset,
    DatasetColumn,
    DataCleaningOperation,
    AnalysisJob,
    AnalysisResult,
    Dashboard,
    AIInsight,
    AuditLog
)


# -------------------------------------------------------------------------
# USER REPOSITORY
# -------------------------------------------------------------------------
class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: Union[str, uuid.UUID]) -> Optional[User]:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        return db.query(User).filter(User.id == uid).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.strip().lower()).first()

    @staticmethod
    def create(
        db: Session,
        full_name: str,
        email: str,
        password_hash: str,
        role: str = "user"
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            full_name=full_name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role.lower(),
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_last_login(db: Session, user_id: Union[str, uuid.UUID]) -> Optional[User]:
        user = UserRepository.get_by_id(db, user_id)
        if user:
            user.last_login = datetime.now()
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 50) -> List[User]:
        return db.query(User).order_by(desc(User.created_at)).offset(skip).limit(limit).all()


# -------------------------------------------------------------------------
# DATASET REPOSITORY (With Strict User-Level Dataset Isolation)
# -------------------------------------------------------------------------
class DatasetRepository:
    @staticmethod
    def create(
        db: Session,
        user_id: Union[str, uuid.UUID],
        dataset_name: str,
        original_filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
        row_count: int = 0,
        column_count: int = 0,
        description: str = ""
    ) -> Dataset:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        dataset = Dataset(
            id=uuid.uuid4(),
            user_id=uid,
            dataset_name=dataset_name,
            original_filename=original_filename,
            file_type=file_type.lower(),
            file_size=file_size,
            storage_path=storage_path,
            row_count=row_count,
            column_count=column_count,
            description=description,
            status="active"
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return dataset

    @staticmethod
    def get_by_id(db: Session, dataset_id: Union[str, uuid.UUID]) -> Optional[Dataset]:
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        return db.query(Dataset).filter(Dataset.id == did).first()

    @staticmethod
    def list_by_user(
        db: Session,
        user_id: Union[str, uuid.UUID],
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dataset]:
        """Strict isolation: Standard users only retrieve their own datasets; admins see all."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        query = db.query(Dataset).filter(Dataset.status != "deleted")
        if not is_admin:
            query = query.filter(Dataset.user_id == uid)
        return query.order_by(desc(Dataset.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, dataset_id: Union[str, uuid.UUID], **kwargs) -> Optional[Dataset]:
        dataset = DatasetRepository.get_by_id(db, dataset_id)
        if not dataset:
            return None
        for key, value in kwargs.items():
            if hasattr(dataset, key) and value is not None:
                setattr(dataset, key, value)
        db.commit()
        db.refresh(dataset)
        return dataset

    @staticmethod
    def delete(db: Session, dataset_id: Union[str, uuid.UUID], hard_delete: bool = False) -> bool:
        dataset = DatasetRepository.get_by_id(db, dataset_id)
        if not dataset:
            return False
        if hard_delete:
            db.delete(dataset)
        else:
            dataset.status = "deleted"
        db.commit()
        return True

    @staticmethod
    def add_columns(db: Session, dataset_id: Union[str, uuid.UUID], columns_data: List[Dict[str, Any]]) -> List[DatasetColumn]:
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        created_cols = []
        for col in columns_data:
            col_record = DatasetColumn(
                id=uuid.uuid4(),
                dataset_id=did,
                column_name=col.get("column_name", "unnamed"),
                data_type=col.get("data_type", "string"),
                null_count=int(col.get("null_count", 0)),
                unique_count=int(col.get("unique_count", 0)),
                min_value=str(col.get("min_value")) if col.get("min_value") is not None else None,
                max_value=str(col.get("max_value")) if col.get("max_value") is not None else None,
                mean_value=float(col.get("mean_value")) if col.get("mean_value") is not None else None,
                median_value=float(col.get("median_value")) if col.get("median_value") is not None else None
            )
            db.add(col_record)
            created_cols.append(col_record)
        db.commit()
        return created_cols

    @staticmethod
    def get_columns(db: Session, dataset_id: Union[str, uuid.UUID]) -> List[DatasetColumn]:
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        return db.query(DatasetColumn).filter(DatasetColumn.dataset_id == did).all()


# -------------------------------------------------------------------------
# DATA CLEANING REPOSITORY
# -------------------------------------------------------------------------
class CleaningRepository:
    @staticmethod
    def log_operation(
        db: Session,
        dataset_id: Union[str, uuid.UUID],
        user_id: Union[str, uuid.UUID],
        operation_type: str,
        column_name: Optional[str] = None,
        operation_details: Optional[Dict[str, Any]] = None,
        rows_affected: int = 0
    ) -> DataCleaningOperation:
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        op = DataCleaningOperation(
            id=uuid.uuid4(),
            dataset_id=did,
            user_id=uid,
            operation_type=operation_type,
            column_name=column_name,
            operation_details=operation_details or {},
            rows_affected=rows_affected,
            status="completed"
        )
        db.add(op)
        db.commit()
        db.refresh(op)
        return op

    @staticmethod
    def list_by_dataset(db: Session, dataset_id: Union[str, uuid.UUID]) -> List[DataCleaningOperation]:
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        return db.query(DataCleaningOperation).filter(DataCleaningOperation.dataset_id == did).order_by(desc(DataCleaningOperation.created_at)).all()


# -------------------------------------------------------------------------
# ANALYSIS REPOSITORY
# -------------------------------------------------------------------------
class AnalysisRepository:
    @staticmethod
    def create_job(
        db: Session,
        dataset_id: Union[str, uuid.UUID],
        user_id: Union[str, uuid.UUID],
        job_type: str
    ) -> AnalysisJob:
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        job = AnalysisJob(
            id=uuid.uuid4(),
            dataset_id=did,
            user_id=uid,
            job_type=job_type,
            status="pending"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_job(db: Session, job_id: Union[str, uuid.UUID]) -> Optional[AnalysisJob]:
        jid = uuid.UUID(str(job_id)) if isinstance(job_id, str) else job_id
        return db.query(AnalysisJob).filter(AnalysisJob.id == jid).first()

    @staticmethod
    def update_job_status(
        db: Session,
        job_id: Union[str, uuid.UUID],
        status: str,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        result_location: Optional[str] = None
    ) -> Optional[AnalysisJob]:
        job = AnalysisRepository.get_job(db, job_id)
        if job:
            job.status = status
            if completed_at:
                job.completed_at = completed_at
            if error_message:
                job.error_message = error_message
            if result_location:
                job.result_location = result_location
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def add_result(
        db: Session,
        job_id: Union[str, uuid.UUID],
        dataset_id: Union[str, uuid.UUID],
        result_type: str,
        result_data: Dict[str, Any]
    ) -> AnalysisResult:
        jid = uuid.UUID(str(job_id)) if isinstance(job_id, str) else job_id
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        res = AnalysisResult(
            id=uuid.uuid4(),
            job_id=jid,
            dataset_id=did,
            result_type=result_type,
            result_data=result_data
        )
        db.add(res)
        db.commit()
        db.refresh(res)
        return res

    @staticmethod
    def get_results_by_job(db: Session, job_id: Union[str, uuid.UUID]) -> List[AnalysisResult]:
        jid = uuid.UUID(str(job_id)) if isinstance(job_id, str) else job_id
        return db.query(AnalysisResult).filter(AnalysisResult.job_id == jid).all()


# -------------------------------------------------------------------------
# DASHBOARD REPOSITORY
# -------------------------------------------------------------------------
class DashboardRepository:
    @staticmethod
    def create(
        db: Session,
        user_id: Union[str, uuid.UUID],
        dashboard_name: str,
        description: str = "",
        configuration: Optional[Dict[str, Any]] = None,
        dataset_id: Optional[Union[str, uuid.UUID]] = None,
        is_public: bool = False
    ) -> Dashboard:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        did = uuid.UUID(str(dataset_id)) if dataset_id else None
        d = Dashboard(
            id=uuid.uuid4(),
            user_id=uid,
            dataset_id=did,
            dashboard_name=dashboard_name,
            description=description,
            configuration=configuration or {},
            is_public=is_public
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        return d

    @staticmethod
    def get_by_id(db: Session, dashboard_id: Union[str, uuid.UUID]) -> Optional[Dashboard]:
        did = uuid.UUID(str(dashboard_id)) if isinstance(dashboard_id, str) else dashboard_id
        return db.query(Dashboard).filter(Dashboard.id == did).first()

    @staticmethod
    def list_by_user(
        db: Session,
        user_id: Union[str, uuid.UUID],
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dashboard]:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        query = db.query(Dashboard)
        if not is_admin:
            query = query.filter((Dashboard.user_id == uid) | (Dashboard.is_public == True))
        return query.order_by(desc(Dashboard.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, dashboard_id: Union[str, uuid.UUID], **kwargs) -> Optional[Dashboard]:
        d = DashboardRepository.get_by_id(db, dashboard_id)
        if not d:
            return None
        for key, value in kwargs.items():
            if hasattr(d, key) and value is not None:
                setattr(d, key, value)
        db.commit()
        db.refresh(d)
        return d

    @staticmethod
    def delete(db: Session, dashboard_id: Union[str, uuid.UUID]) -> bool:
        d = DashboardRepository.get_by_id(db, dashboard_id)
        if not d:
            return False
        db.delete(d)
        db.commit()
        return True


# -------------------------------------------------------------------------
# AI INSIGHTS REPOSITORY
# -------------------------------------------------------------------------
class AIInsightRepository:
    @staticmethod
    def create(
        db: Session,
        user_id: Union[str, uuid.UUID],
        dataset_id: Union[str, uuid.UUID],
        insight_type: str,
        title: str,
        content: str,
        recommendations: Optional[List[Any]] = None,
        analysis_id: Optional[Union[str, uuid.UUID]] = None
    ) -> AIInsight:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        aid = uuid.UUID(str(analysis_id)) if analysis_id else None
        insight = AIInsight(
            id=uuid.uuid4(),
            user_id=uid,
            dataset_id=did,
            analysis_id=aid,
            insight_type=insight_type,
            title=title,
            content=content,
            recommendations=recommendations or []
        )
        db.add(insight)
        db.commit()
        db.refresh(insight)
        return insight

    @staticmethod
    def list_by_dataset(db: Session, dataset_id: Union[str, uuid.UUID]) -> List[AIInsight]:
        did = uuid.UUID(str(dataset_id)) if isinstance(dataset_id, str) else dataset_id
        return db.query(AIInsight).filter(AIInsight.dataset_id == did).order_by(desc(AIInsight.created_at)).all()


# -------------------------------------------------------------------------
# AUDIT LOG REPOSITORY
# -------------------------------------------------------------------------
class AuditLogRepository:
    @staticmethod
    def log(
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[Union[str, uuid.UUID]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        uid = uuid.UUID(str(user_id)) if user_id else None
        entry = AuditLog(
            id=uuid.uuid4(),
            user_id=uid,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            ip_address=ip_address,
            user_agent=user_agent,
            log_metadata=metadata or {}
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def list_logs(
        db: Session,
        user_id: Optional[Union[str, uuid.UUID]] = None,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AuditLog]:
        query = db.query(AuditLog)
        if user_id:
            uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
            query = query.filter(AuditLog.user_id == uid)
        if action:
            query = query.filter(AuditLog.action == action)
        return query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

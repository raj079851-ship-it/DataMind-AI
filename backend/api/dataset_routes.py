# -*- coding: utf-8 -*-
"""
FastAPI Router for Datasets Management.
Implements:
- POST /api/datasets/upload (file upload, pandas profiling, dataset_columns insertion, audit logging)
- GET /api/datasets (user-isolated dataset listing)
- GET /api/datasets/{dataset_id} (dataset detail with column metadata)
- DELETE /api/datasets/{dataset_id} (dataset deletion with audit logging)
- POST /api/datasets/{dataset_id}/clean (cleaning execution, operation logging, column updates)
- POST /api/datasets/{dataset_id}/analyze (analysis job triggering and execution)
"""

import os
import uuid
import re
import shutil
import io
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Dataset
from backend.database.schemas import (
    DatasetResponse,
    DatasetDetailResponse,
    DatasetColumnSchema,
    DataCleaningRequest,
    DataCleaningResponse,
    AnalysisJobCreateRequest,
    AnalysisJobResponse
)
from backend.database.repositories import (
    DatasetRepository,
    CleaningRepository,
    AnalysisRepository,
    AuditLogRepository
)
from backend.authentication.jwt_handler import get_current_active_user, verify_dataset_access
from modules.eda_engine import compute_comprehensive_stats, compute_correlation_analysis

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "datasets"))
os.makedirs(STORAGE_DIR, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', os.path.basename(filename))
    return cleaned or "dataset.csv"


def profile_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generates column profile metadata for dataset_columns table."""
    columns_meta = []
    for col_name in df.columns:
        series = df[col_name]
        col_str = str(col_name)
        
        # Determine data type
        if pd.api.types.is_numeric_dtype(series):
            dtype_label = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            dtype_label = "datetime"
        elif pd.api.types.is_bool_dtype(series):
            dtype_label = "boolean"
        else:
            dtype_label = "categorical" if series.nunique() <= 50 else "text"
            
        null_count = int(series.isna().sum())
        unique_count = int(series.nunique())
        
        min_val = None
        max_val = None
        mean_val = None
        median_val = None
        
        if pd.api.types.is_numeric_dtype(series) and not series.dropna().empty:
            clean_s = series.dropna()
            try:
                min_val = str(round(float(clean_s.min()), 4))
                max_val = str(round(float(clean_s.max()), 4))
                mean_val = round(float(clean_s.mean()), 4)
                median_val = round(float(clean_s.median()), 4)
            except Exception:
                pass
        elif not series.dropna().empty:
            try:
                min_val = str(series.dropna().min())[:50]
                max_val = str(series.dropna().max())[:50]
            except Exception:
                pass
                
        columns_meta.append({
            "column_name": col_str,
            "data_type": dtype_label,
            "null_count": null_count,
            "unique_count": unique_count,
            "min_value": min_val,
            "max_value": max_val,
            "mean_value": mean_val,
            "median_value": median_val
        })
    return columns_meta


@router.post("/upload", response_model=DatasetDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a dataset file (CSV, Excel, JSON, Parquet), stores it on disk,
    profiles columns into PostgreSQL `dataset_columns`, and creates an audit log.
    """
    safe_name = sanitize_filename(file.filename or "dataset.csv")
    ext = os.path.splitext(safe_name)[1].lower()
    
    if ext not in [".csv", ".xlsx", ".xls", ".json", ".parquet"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Supported: .csv, .xlsx, .xls, .json, .parquet"
        )
        
    content = await file.read()
    file_size = len(content)
    if file_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    # Parse into pandas DataFrame
    try:
        buffer = io.BytesIO(content)
        if ext == ".csv":
            df = pd.read_csv(buffer)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(buffer)
        elif ext == ".json":
            df = pd.read_json(buffer)
        elif ext == ".parquet":
            df = pd.read_parquet(buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse uploaded dataset: {str(e)}"
        )

    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    dataset_uuid = uuid.uuid4()
    
    # Save to disk storage
    saved_filename = f"{dataset_uuid}_{safe_name}"
    storage_path = os.path.join(STORAGE_DIR, saved_filename)
    try:
        with open(storage_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not persist file to storage: {str(e)}"
        )

    display_name = dataset_name.strip() if dataset_name and dataset_name.strip() else safe_name

    # 1. Insert into datasets table
    dataset = Dataset(
        id=dataset_uuid,
        user_id=current_user.id,
        dataset_name=display_name,
        original_filename=safe_name,
        file_type=ext.replace(".", ""),
        file_size=file_size,
        storage_path=storage_path,
        row_count=row_count,
        column_count=column_count,
        description=description or "",
        status="active"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # 2. Profile and insert into dataset_columns
    cols_meta = profile_dataframe(df)
    created_columns = DatasetRepository.add_columns(db, dataset.id, cols_meta)

    # 3. Write to audit_logs
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    AuditLogRepository.log(
        db=db,
        action="UPLOAD_DATASET",
        resource_type="dataset",
        resource_id=str(dataset.id),
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        metadata={
            "dataset_name": dataset.dataset_name,
            "filename": safe_name,
            "rows": row_count,
            "columns": column_count,
            "size_bytes": file_size
        }
    )

    col_schemas = [
        DatasetColumnSchema(
            id=str(c.id),
            column_name=c.column_name,
            data_type=c.data_type,
            null_count=c.null_count,
            unique_count=c.unique_count,
            min_value=c.min_value,
            max_value=c.max_value,
            mean_value=c.mean_value,
            median_value=c.median_value,
            created_at=c.created_at.isoformat() if c.created_at else None
        )
        for c in created_columns
    ]

    return DatasetDetailResponse(
        id=str(dataset.id),
        user_id=str(dataset.user_id),
        dataset_name=dataset.dataset_name,
        original_filename=dataset.original_filename,
        file_type=dataset.file_type,
        file_size=dataset.file_size,
        storage_path=dataset.storage_path,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        description=dataset.description,
        status=dataset.status,
        created_at=dataset.created_at.isoformat() if dataset.created_at else None,
        updated_at=dataset.updated_at.isoformat() if dataset.updated_at else None,
        columns=col_schemas
    )


@router.get("", response_model=List[DatasetResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lists datasets accessible to the user (strict isolation: non-admins only see their own)."""
    is_admin = current_user.role.lower() == "admin"
    datasets = DatasetRepository.list_by_user(db, current_user.id, is_admin=is_admin, skip=skip, limit=limit)
    
    if search:
        search_lower = search.lower()
        datasets = [d for d in datasets if search_lower in d.dataset_name.lower() or search_lower in d.original_filename.lower()]

    return [
        DatasetResponse(
            id=str(d.id),
            user_id=str(d.user_id),
            dataset_name=d.dataset_name,
            original_filename=d.original_filename,
            file_type=d.file_type,
            file_size=d.file_size,
            storage_path=d.storage_path,
            row_count=d.row_count,
            column_count=d.column_count,
            description=d.description,
            status=d.status,
            created_at=d.created_at.isoformat() if d.created_at else None,
            updated_at=d.updated_at.isoformat() if d.updated_at else None
        )
        for d in datasets
    ]


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: str,
    dataset: Dataset = Depends(verify_dataset_access),
    db: Session = Depends(get_db)
):
    """Retrieves dataset details with column metadata."""
    columns = DatasetRepository.get_columns(db, dataset.id)
    col_schemas = [
        DatasetColumnSchema(
            id=str(c.id),
            column_name=c.column_name,
            data_type=c.data_type,
            null_count=c.null_count,
            unique_count=c.unique_count,
            min_value=c.min_value,
            max_value=c.max_value,
            mean_value=c.mean_value,
            median_value=c.median_value,
            created_at=c.created_at.isoformat() if c.created_at else None
        )
        for c in columns
    ]

    return DatasetDetailResponse(
        id=str(dataset.id),
        user_id=str(dataset.user_id),
        dataset_name=dataset.dataset_name,
        original_filename=dataset.original_filename,
        file_type=dataset.file_type,
        file_size=dataset.file_size,
        storage_path=dataset.storage_path,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        description=dataset.description,
        status=dataset.status,
        created_at=dataset.created_at.isoformat() if dataset.created_at else None,
        updated_at=dataset.updated_at.isoformat() if dataset.updated_at else None,
        columns=col_schemas
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
def delete_dataset(
    dataset_id: str,
    request: Request = None,
    dataset: Dataset = Depends(verify_dataset_access),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deletes dataset (cascade deletes columns/jobs/results in DB) and removes stored file."""
    file_path = dataset.storage_path
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    DatasetRepository.delete(db, dataset.id, hard_delete=True)

    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    AuditLogRepository.log(
        db=db,
        action="DELETE_DATASET",
        resource_type="dataset",
        resource_id=str(dataset.id),
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        metadata={"deleted_dataset_name": dataset.dataset_name}
    )

    return {"status": "success", "message": f"Dataset '{dataset.dataset_name}' deleted successfully."}


@router.post("/{dataset_id}/clean", response_model=DataCleaningResponse)
def clean_dataset(
    dataset_id: str,
    payload: DataCleaningRequest,
    request: Request = None,
    dataset: Dataset = Depends(verify_dataset_access),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Executes a data cleaning operation, saves updated file, and logs to data_cleaning_operations."""
    file_path = dataset.storage_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset storage file not found.")

    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path)
        elif file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read dataset: {str(e)}")

    original_rows = len(df)
    col = payload.column_name
    op_type = payload.operation_type.lower()
    details = payload.operation_details or {}

    rows_affected = 0
    if op_type == "handle_missing_values" or op_type == "impute":
        strategy = details.get("strategy", "mean")
        if col and col in df.columns:
            null_mask = df[col].isna()
            rows_affected = int(null_mask.sum())
            if pd.api.types.is_numeric_dtype(df[col]):
                if strategy == "mean":
                    df[col] = df[col].fillna(df[col].mean())
                elif strategy == "median":
                    df[col] = df[col].fillna(df[col].median())
                elif strategy == "mode":
                    df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 0)
                elif strategy == "zero":
                    df[col] = df[col].fillna(0)
            else:
                fill_val = details.get("fill_value", "Unknown")
                df[col] = df[col].fillna(fill_val)
        else:
            # Impute all
            rows_affected = int(df.isna().sum().sum())
            for c in df.columns:
                if pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].mean() if not df[c].dropna().empty else 0)
                else:
                    df[c] = df[c].fillna("Unknown")

    elif op_type == "drop_duplicates" or op_type == "remove_duplicates":
        subset = [col] if col and col in df.columns else None
        dups = df.duplicated(subset=subset).sum()
        rows_affected = int(dups)
        df = df.drop_duplicates(subset=subset)

    elif op_type == "drop_na" or op_type == "remove_nulls":
        if col and col in df.columns:
            rows_affected = int(df[col].isna().sum())
            df = df.dropna(subset=[col])
        else:
            rows_affected = original_rows - len(df.dropna())
            df = df.dropna()

    elif op_type == "handle_outliers":
        if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            rows_affected = int(outlier_mask.sum())
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
    else:
        rows_affected = 0

    # Save cleaned file back to disk
    if file_path.endswith(".csv"):
        df.to_csv(file_path, index=False)
    elif file_path.endswith((".xlsx", ".xls")):
        df.to_excel(file_path, index=False)
    elif file_path.endswith(".json"):
        df.to_json(file_path, orient="records")
    elif file_path.endswith(".parquet"):
        df.to_parquet(file_path, index=False)
        
    new_size = os.path.getsize(file_path)
    DatasetRepository.update(
        db,
        dataset.id,
        row_count=int(df.shape[0]),
        column_count=int(df.shape[1]),
        file_size=new_size
    )

    # Log to data_cleaning_operations
    op = CleaningRepository.log_operation(
        db=db,
        dataset_id=dataset.id,
        user_id=current_user.id,
        operation_type=op_type,
        column_name=col,
        operation_details=details,
        rows_affected=rows_affected
    )

    # Log to audit_logs
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    AuditLogRepository.log(
        db=db,
        action="DATA_CLEANING_OPERATION",
        resource_type="dataset",
        resource_id=str(dataset.id),
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        metadata={"operation": op_type, "column": col, "rows_affected": rows_affected}
    )

    return DataCleaningResponse(
        id=str(op.id),
        dataset_id=str(op.dataset_id),
        user_id=str(op.user_id),
        operation_type=op.operation_type,
        column_name=op.column_name,
        operation_details=op.operation_details or {},
        rows_affected=op.rows_affected,
        status=op.status,
        created_at=op.created_at.isoformat() if op.created_at else None
    )


@router.post("/{dataset_id}/analyze", response_model=AnalysisJobResponse)
def analyze_dataset(
    dataset_id: str,
    payload: AnalysisJobCreateRequest,
    request: Request = None,
    dataset: Dataset = Depends(verify_dataset_access),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Queues/triggers an analysis job and generates an analysis_results entry."""
    file_path = dataset.storage_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file not found for analysis.")

    # Create job entry
    job = AnalysisRepository.create_job(
        db=db,
        dataset_id=dataset.id,
        user_id=current_user.id,
        job_type=payload.job_type
    )

    try:
        df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)
    except Exception:
        df = pd.read_csv(file_path, on_bad_lines="skip")

    try:
        # Run empirical analysis based on job_type
        jtype = payload.job_type.upper()
        if "EDA" in jtype or "SUMMARY" in jtype:
            summary = compute_comprehensive_stats(df)
            AnalysisRepository.add_result(
                db=db,
                job_id=job.id,
                dataset_id=dataset.id,
                result_type="EDA_SUMMARY",
                result_data=summary
            )
        elif "CORRELATION" in jtype:
            corrs = compute_correlation_analysis(df)
            AnalysisRepository.add_result(
                db=db,
                job_id=job.id,
                dataset_id=dataset.id,
                result_type="CORRELATION_MATRIX",
                result_data=corrs
            )
        else:
            summary = compute_comprehensive_stats(df)
            AnalysisRepository.add_result(
                db=db,
                job_id=job.id,
                dataset_id=dataset.id,
                result_type=f"{jtype}_RESULT",
                result_data={"rows": len(df), "columns": list(df.columns), "summary": summary.get("summary", {})}
            )

        updated_job = AnalysisRepository.update_job_status(
            db=db,
            job_id=job.id,
            status="completed",
            completed_at=datetime.now()
        )
    except Exception as e:
        updated_job = AnalysisRepository.update_job_status(
            db=db,
            job_id=job.id,
            status="failed",
            error_message=str(e)
        )

    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    AuditLogRepository.log(
        db=db,
        action="TRIGGER_ANALYSIS",
        resource_type="analysis_job",
        resource_id=str(job.id),
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        metadata={"job_type": payload.job_type, "status": updated_job.status}
    )

    return AnalysisJobResponse(
        id=str(updated_job.id),
        dataset_id=str(updated_job.dataset_id),
        user_id=str(updated_job.user_id),
        job_type=updated_job.job_type,
        status=updated_job.status,
        started_at=updated_job.started_at.isoformat() if updated_job.started_at else None,
        completed_at=updated_job.completed_at.isoformat() if updated_job.completed_at else None,
        error_message=updated_job.error_message,
        result_location=updated_job.result_location
    )

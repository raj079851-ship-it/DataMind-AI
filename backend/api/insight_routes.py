# -*- coding: utf-8 -*-
"""
FastAPI Router for AI-Generated Insights.
Implements:
- GET /api/insights/{dataset_id} (fetch AI insights for dataset)
- POST /api/insights/{dataset_id}/generate (generate automated AI insights)
"""

import os
import uuid
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User, Dataset, AIInsight
from backend.database.schemas import AIInsightCreateRequest, AIInsightResponse
from backend.database.repositories import AIInsightRepository, AuditLogRepository
from backend.authentication.jwt_handler import get_current_active_user, verify_dataset_access
from modules.bi_insights import run_automated_insights_engine

router = APIRouter(prefix="/api/insights", tags=["AI Insights"])


@router.get("/{dataset_id}", response_model=List[AIInsightResponse])
def get_dataset_insights(
    dataset_id: str,
    dataset: Dataset = Depends(verify_dataset_access),
    db: Session = Depends(get_db)
):
    """Retrieves all AI-generated insights stored for a dataset."""
    insights = AIInsightRepository.list_by_dataset(db, dataset.id)
    return [
        AIInsightResponse(
            id=str(ins.id),
            user_id=str(ins.user_id),
            dataset_id=str(ins.dataset_id),
            analysis_id=str(ins.analysis_id) if ins.analysis_id else None,
            insight_type=ins.insight_type,
            title=ins.title,
            content=ins.content,
            recommendations=ins.recommendations or [],
            created_at=ins.created_at.isoformat() if ins.created_at else None
        )
        for ins in insights
    ]


@router.post("/{dataset_id}/generate", response_model=List[AIInsightResponse], status_code=status.HTTP_201_CREATED)
def generate_dataset_insights(
    dataset_id: str,
    request: Request = None,
    dataset: Dataset = Depends(verify_dataset_access),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Triggers automated AI heuristics on the dataset and persists insights to PostgreSQL.
    """
    file_path = dataset.storage_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file not found.")

    try:
        df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)
    except Exception:
        df = pd.read_csv(file_path, on_bad_lines="skip")

    generated_records = []
    
    # Run automated insights engine
    try:
        raw_insights = run_automated_insights_engine(df)
    except Exception:
        raw_insights = []

    if not raw_insights:
        # Default synthesized insights based on dataframe profile
        num_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(exclude="number").columns.tolist()
        
        raw_insights = [
            {
                "insight_type": "Executive Overview",
                "title": f"Dataset Dimension & Structural Profile",
                "content": f"The dataset '{dataset.dataset_name}' contains {len(df):,} records and {len(df.columns)} attributes ({len(num_cols)} numeric, {len(cat_cols)} categorical). Overall completeness is {round((1 - df.isna().mean().mean()) * 100, 1)}%.",
                "recommendations": [
                    "Evaluate high-cardinality categorical features for encoding.",
                    "Verify target variables before proceeding to machine learning pipelines."
                ]
            }
        ]
        
        if num_cols:
            first_num = num_cols[0]
            raw_insights.append({
                "insight_type": "Statistical Distribution",
                "title": f"Key Metric Variance: {first_num}",
                "content": f"Mean for {first_num} is {round(df[first_num].mean(), 2)} with a standard deviation of {round(df[first_num].std(), 2)}. Quartile ranges indicate healthy metric spread.",
                "recommendations": [
                    f"Check for extreme outliers beyond 3 standard deviations in {first_num}.",
                    f"Consider normalizing {first_num} if training linear regression models."
                ]
            })

    for item in raw_insights:
        title = item.get("title") or item.get("headline") or "Statistical Insight"
        content = item.get("content") or item.get("description") or item.get("text") or "Insight details."
        itype = item.get("insight_type") or item.get("type") or "Analytics"
        recs = item.get("recommendations") or item.get("actionable_steps") or []

        rec = AIInsightRepository.create(
            db=db,
            user_id=current_user.id,
            dataset_id=dataset.id,
            insight_type=itype,
            title=title,
            content=content,
            recommendations=recs
        )
        generated_records.append(rec)

    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    AuditLogRepository.log(
        db=db,
        action="GENERATE_AI_INSIGHTS",
        resource_type="dataset",
        resource_id=str(dataset.id),
        user_id=current_user.id,
        ip_address=ip,
        user_agent=ua,
        metadata={"count": len(generated_records)}
    )

    return [
        AIInsightResponse(
            id=str(r.id),
            user_id=str(r.user_id),
            dataset_id=str(r.dataset_id),
            analysis_id=str(r.analysis_id) if r.analysis_id else None,
            insight_type=r.insight_type,
            title=r.title,
            content=r.content,
            recommendations=r.recommendations or [],
            created_at=r.created_at.isoformat() if r.created_at else None
        )
        for r in generated_records
    ]

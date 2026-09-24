# -*- coding: utf-8 -*-
"""
DataMind AI - Enterprise PostgreSQL Backend Application.
Assembles the complete REST API architecture with:
- Authentication & RBAC (/api/auth)
- Dataset Lifecycle & Column Profiling (/api/datasets)
- Analysis Pipelines & Jobs (/api/analysis)
- Interactive Dashboards (/api/dashboards)
- AI-Driven Insights (/api/insights)
- Audit Logging & Compliance (/api/audit-logs)
- Database Diagnostics & Health Checks (/api/health, /api/db-status)
"""

import time
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database.connection import get_db, check_db_connection, engine
from backend.database.schemas import DatabaseHealthResponse
from backend.api.auth_routes import router as auth_router
from backend.api.dataset_routes import router as dataset_router
from backend.api.analysis_routes import router as analysis_router
from backend.api.dashboard_routes import router as dashboard_router
from backend.api.insight_routes import router as insight_router
from backend.api.audit_routes import router as audit_router

app = FastAPI(
    title="DataMind AI - PostgreSQL Relational Backend",
    description="Production-Grade Relational Core for AI-Powered Data Analytics Platform",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all domain routers under /api
app.include_router(auth_router)
app.include_router(dataset_router)
app.include_router(analysis_router)
app.include_router(dashboard_router)
app.include_router(insight_router)
app.include_router(audit_router)


@app.get("/api/health", response_model=DatabaseHealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Validates PostgreSQL connectivity, pool status, and table presence."""
    diag = check_db_connection()
    if diag.get("status") != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity failure: {diag.get('error')}"
        )

    # Fetch PostgreSQL version
    version_row = db.execute(text("SELECT version();")).fetchone()
    version_str = version_row[0] if version_row else "Unknown"

    pool = engine.pool
    pool_stats = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow()
    }

    return DatabaseHealthResponse(
        status="healthy",
        engine="PostgreSQL",
        version=version_str,
        database=diag.get("database", "analytics_platform"),
        user=diag.get("user", "postgres"),
        host=diag.get("host", "localhost"),
        port=diag.get("port", "5432"),
        tables_count=diag.get("tables_count", 0),
        tables=diag.get("tables", []),
        pool=pool_stats
    )


@app.get("/api/db-status")
def database_status(db: Session = Depends(get_db)):
    """Returns row counts and metadata across all 9 platform tables."""
    start_time = time.time()
    
    tables = [
        "users",
        "datasets",
        "dataset_columns",
        "data_cleaning_operations",
        "analysis_jobs",
        "analysis_results",
        "dashboards",
        "ai_insights",
        "audit_logs"
    ]
    
    counts = {}
    for tbl in tables:
        try:
            res = db.execute(text(f"SELECT COUNT(*) FROM {tbl};")).fetchone()
            counts[tbl] = res[0] if res else 0
        except Exception:
            counts[tbl] = 0

    latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "status": "online",
        "database": "analytics_platform",
        "engine": "PostgreSQL 18",
        "latency_ms": latency_ms,
        "table_row_counts": counts,
        "active_pool_connections": engine.pool.checkedout(),
        "total_records_tracked": sum(counts.values())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

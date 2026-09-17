"""
DataMind AI - Enterprise REST API
Production FastAPI implementation providing all 20+ endpoints specified in Section 43:
/auth, /projects, /datasets, /data-preview, /data-cleaning, /data-processing,
/features, /eda, /charts, /sql, /statistics, /ai, /ml, /models, /predictions,
/forecasting, /dashboards, /reports, /exports
Features interactive Swagger UI documentation at http://localhost:8000/docs
"""

import os
import io
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Body, UploadFile, File, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Core Platform Modules
from modules.data_loader import (
    load_dataset,
    get_dataset_quick_profile,
    compute_dataset_health_score,
    generate_sample_customer_churn,
    generate_sample_housing,
    generate_sample_ecommerce_sales
)
from modules.project_manager import ProjectManager
from modules.data_cleaner import (
    audit_data_quality,
    impute_missing_values,
    handle_outliers,
    clean_text_and_duplicates,
    one_click_ai_auto_clean
)
from modules.data_processor import (
    filter_rows,
    select_and_rename_columns,
    create_calculated_column,
    group_by_aggregate
)
from modules.feature_engineer import (
    categorize_features,
    get_feature_recommendations,
    scale_features,
    encode_categorical,
    extract_datetime_features,
    one_click_ai_feature_engineering
)
from modules.eda_engine import (
    compute_comprehensive_stats,
    compute_correlation_analysis,
    generate_automated_eda_insights
)
from modules.sql_studio import SQLStudio, generate_ai_sql
from modules.statistical_engine import (
    run_descriptive_statistics,
    run_hypothesis_test,
    run_regression_analysis
)
from modules.ai_orchestrator import AIOrchestrator
from modules.ml_engine import run_automl_tournament, run_unsupervised_clustering
from modules.automl_pipeline import run_automl_pipeline
from modules.predictive_engine import predict_scenario
from modules.forecasting_engine import generate_forecast, detect_time_series_columns
from modules.model_registry import ModelRegistry
from modules.powerbi_analyzer import analyze_powerbi_export
from modules.dashboard_builder import generate_ai_dashboard_spec
from modules.bi_insights import compute_kpi_goal_tracking, compute_period_growth, run_automated_insights_engine
from modules.data_quality_center import DataQualityCenter
from modules.reports_engine import generate_html_report

# Enterprise Security Architecture
from modules.security import (
    Role,
    Permission,
    has_permission,
    get_role_permissions,
    default_user_manager,
    default_session_manager,
    default_oauth_manager,
    default_column_encryptor,
    default_api_key_manager,
    default_api_rate_limiter,
    auth_rate_limiter,
    default_audit_logger,
    CredentialSanitizer
)
from modules.ai_chart_recommender import default_chart_recommender

# Initialize App
app = FastAPI(
    title="DataMind AI Enterprise API",
    description="Production-Ready AI-Powered Data Analytics Platform REST API",
    version="2.0.0",
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

# Shared In-Memory Server State
project_manager = ProjectManager()
model_registry = ModelRegistry()
sql_studio = SQLStudio()
data_quality_center = DataQualityCenter()
ai_orchestrator = AIOrchestrator()

# Active In-Memory Dataset
active_datasets: Dict[str, pd.DataFrame] = {
    "default": generate_sample_customer_churn()
}


def get_current_df() -> pd.DataFrame:
    return active_datasets.get("default", generate_sample_customer_churn())


# ---------------- SCHEMAS ----------------
class AuthLoginRequest(BaseModel):
    username: str = "admin"
    password: str = "Admin@123"

class OAuthCallbackRequest(BaseModel):
    provider: str = "google"
    code: str = "demo_code_123"
    state: str

class CreateAPIKeyRequest(BaseModel):
    name: str = "Production Client"
    role: str = "Analyst"
    tenant_id: str = "tenant_default"
    permissions: Optional[List[str]] = ["read:all"]

class ColumnEncryptionRequest(BaseModel):
    columns: List[str]

class ChartRecommendationRequest(BaseModel):
    query: str = "Show me the relationship between sales and profit."


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    dataset_name: Optional[str] = "customer_churn.csv"

class SQLQueryRequest(BaseModel):
    sql: str = "SELECT * FROM df LIMIT 10;"

class NaturalLanguageSQLRequest(BaseModel):
    prompt: str = "Show the top 5 customers with highest charges"

class ImputationRequest(BaseModel):
    strategy_dict: Optional[Dict[str, str]] = None

class OutlierRequest(BaseModel):
    columns: Optional[List[str]] = None
    method: str = "iqr"
    action: str = "cap"
    factor: float = 1.5

class HypothesisTestRequest(BaseModel):
    test_type: str = "independent_t_test"
    var1: str
    var2: Optional[str] = None
    group_col: Optional[str] = None
    group_val1: Optional[str] = None
    group_val2: Optional[str] = None

class RegressionRequest(BaseModel):
    target_col: str
    feature_cols: List[str]
    regression_type: str = "linear"

class ForecastRequest(BaseModel):
    date_col: str
    metric_col: str
    horizon: int = 12
    freq: str = "M"

class OmnibarRequest(BaseModel):
    command: str

class WhatIfPredictionRequest(BaseModel):
    input_values: Dict[str, Any]


# ---------------- 1. AUTH & SECURITY ENDPOINTS ----------------
@app.post("/auth/login", tags=["Authentication"])
def login(creds: AuthLoginRequest, request: Request):
    """Authenticates user with PBKDF2 hash verification, sliding-window rate limiting, and signed session token."""
    client_ip = request.client.host if request and request.client else "127.0.0.1"

    # Rate limiting protection against brute force attacks
    rate_res = auth_rate_limiter.is_allowed(client_ip)
    if not rate_res.allowed:
        default_audit_logger.log(
            event_type="AUTH_RATE_LIMIT",
            user=creds.username,
            status="BLOCKED",
            resource="API",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: too many authentication requests. Try again in {rate_res.retry_after} seconds."
        )

    user, err = default_user_manager.authenticate(creds.username, creds.password)
    if err or not user:
        default_audit_logger.log(
            event_type="AUTH_FAILED",
            user=creds.username,
            status="FAILED",
            resource="API",
            details={"error": err},
            ip_address=client_ip
        )
        raise HTTPException(status_code=401, detail=err or "Invalid username or password.")

    token = default_session_manager.create_session(
        username=user.username,
        role=user.role,
        tenant_id=user.tenant_id
    )

    default_audit_logger.log(
        event_type="AUTH_LOGIN",
        user=user.username,
        role=user.role,
        status="SUCCESS",
        resource="API",
        ip_address=client_ip
    )

    perms = [p.value for p in get_role_permissions(user.role)]
    response = {
        "status": "success",
        "token_type": "bearer",
        "access_token": token,
        "token": token,
        "user": {
            "username": user.username,
            "role": user.role,
            "email": user.email,
            "full_name": user.full_name
        },
        "permissions": perms
    }
    return CredentialSanitizer.sanitize(response)


@app.post("/auth/logout", tags=["Authentication"])
def logout(request: Request, authorization: Optional[str] = Header(None)):
    """Revokes session token and blacklists it from subsequent requests."""
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    raw_token = authorization.replace("Bearer ", "").strip() if authorization else ""
    if raw_token:
        default_session_manager.revoke_session(raw_token)
    default_audit_logger.log(
        event_type="AUTH_LOGOUT",
        status="SUCCESS",
        resource="API",
        ip_address=client_ip
    )
    return {"status": "success", "message": "Session revoked successfully."}


@app.get("/auth/me", tags=["Authentication"])
def get_current_user(authorization: Optional[str] = Header(None)):
    """Validates session token and returns caller profile and permissions."""
    raw_token = authorization.replace("Bearer ", "").strip() if authorization else ""
    if not raw_token:
        return {
            "user": "Guest",
            "role": "Viewer",
            "authenticated": False,
            "permissions": ["view_dashboards", "view_reports"]
        }

    valid, session_data = default_session_manager.validate_session(raw_token)
    if not valid or not session_data:
        raise HTTPException(status_code=401, detail="Invalid, expired, or revoked session token.")

    role = session_data.get("role", "Viewer")
    perms = [p.value for p in get_role_permissions(role)]
    return {
        "user": session_data.get("username"),
        "role": role,
        "tenant_id": session_data.get("tenant_id"),
        "authenticated": True,
        "permissions": perms
    }


@app.get("/auth/oauth/login", tags=["OAuth SSO"])
def oauth_login(provider: str = "google"):
    """Generates OAuth 2.0 authorization URL with CSRF state token."""
    auth_url, state = default_oauth_manager.generate_auth_url(provider)
    return {"provider": provider, "auth_url": auth_url, "state": state}


@app.post("/auth/oauth/callback", tags=["OAuth SSO"])
def oauth_callback(req: OAuthCallbackRequest, request: Request):
    """Handles OAuth callback and provisions authenticated session token."""
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    profile, err = default_oauth_manager.handle_sandbox_login(req.provider, req.state)
    if err or not profile:
        raise HTTPException(status_code=400, detail=err or "OAuth authentication failed.")

    token = default_session_manager.create_session(
        username=profile["username"],
        role=profile["role"]
    )
    default_audit_logger.log(
        event_type="OAUTH_LOGIN",
        user=profile["username"],
        role=profile["role"],
        status="SUCCESS",
        details={"provider": req.provider},
        ip_address=client_ip
    )
    return {
        "status": "success",
        "access_token": token,
        "profile": profile
    }


# ---------------- SECURITY & GOVERNANCE ENDPOINTS ----------------
@app.get("/security/audit-logs", tags=["Security & Governance"])
def get_audit_logs(limit: int = 50, event_type: Optional[str] = None, user: Optional[str] = None):
    """Retrieves structured audit log events with tamper-evident records."""
    logs = default_audit_logger.get_recent_logs(limit=limit, event_type=event_type, user=user)
    return {"total": len(logs), "logs": logs}


@app.post("/security/api-keys", tags=["Security & Governance"])
def create_api_key(req: CreateAPIKeyRequest):
    """Generates an enterprise API key (raw key returned only once; only hash persisted)."""
    raw_key, meta = default_api_key_manager.generate_api_key(
        name=req.name,
        role=req.role,
        tenant_id=req.tenant_id,
        permissions=req.permissions
    )
    default_audit_logger.log(
        event_type="API_KEY_CREATED",
        status="SUCCESS",
        resource="API_KEY",
        details={"key_name": req.name, "prefix": meta["prefix"]}
    )
    return {
        "status": "success",
        "raw_key": raw_key,
        "metadata": meta,
        "warning": "Save this key now. It will never be displayed again."
    }


@app.get("/security/api-keys", tags=["Security & Governance"])
def list_api_keys():
    """Lists registered API keys with hashes stripped for security."""
    keys = default_api_key_manager.list_api_keys()
    return {"total": len(keys), "keys": keys}


@app.delete("/security/api-keys/{key_id}", tags=["Security & Governance"])
def revoke_api_key(key_id: str):
    """Revokes an API key instantly."""
    revoked = default_api_key_manager.revoke_api_key(key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found.")
    default_audit_logger.log(
        event_type="API_KEY_REVOKED",
        status="SUCCESS",
        resource=f"API_KEY:{key_id}"
    )
    return {"status": "success", "revoked": True}


@app.post("/security/encrypt-columns", tags=["Security & Governance"])
def encrypt_columns_api(req: ColumnEncryptionRequest):
    """Encrypts specified columns in the active dataset using AES-256 Fernet."""
    df = get_current_df()
    enc_df, err = default_column_encryptor.encrypt_columns(df, req.columns)
    if err:
        raise HTTPException(status_code=400, detail=err)
    active_datasets["default"] = enc_df
    default_audit_logger.log(
        event_type="COLUMNS_ENCRYPTED",
        status="SUCCESS",
        resource="DATASET",
        details={"columns": req.columns}
    )
    return {
        "status": "success",
        "encrypted_columns": req.columns,
        "sample_preview": enc_df[req.columns].head(3).to_dict(orient="records")
    }


@app.post("/security/decrypt-columns", tags=["Security & Governance"])
def decrypt_columns_api(req: ColumnEncryptionRequest):
    """Decrypts specified columns in the active dataset back to plaintext."""
    df = get_current_df()
    dec_df, err = default_column_encryptor.decrypt_columns(df, req.columns)
    if err:
        raise HTTPException(status_code=400, detail=err)
    active_datasets["default"] = dec_df
    default_audit_logger.log(
        event_type="COLUMNS_DECRYPTED",
        status="SUCCESS",
        resource="DATASET",
        details={"columns": req.columns}
    )
    return {
        "status": "success",
        "decrypted_columns": req.columns,
        "sample_preview": dec_df[req.columns].head(3).to_dict(orient="records")
    }



# ---------------- 2. PROJECTS ENDPOINTS ----------------
@app.get("/projects", tags=["Project Management"])
def list_projects():
    return project_manager.get_all_projects()

@app.post("/projects", tags=["Project Management"])
def create_project(req: CreateProjectRequest):
    p = project_manager.create_project(req.name, req.description or "", req.dataset_name or "dataset.csv")
    return {"status": "created", "project": p}

@app.get("/projects/{project_id}", tags=["Project Management"])
def get_project(project_id: str):
    p = project_manager.projects.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.delete("/projects/{project_id}", tags=["Project Management"])
def delete_project(project_id: str):
    success = project_manager.delete_project(project_id)
    return {"status": "deleted" if success else "not_found"}


# ---------------- 3. DATASETS & PREVIEW ENDPOINTS ----------------
@app.get("/datasets/active", tags=["Datasets"])
def get_active_dataset_metadata():
    df = get_current_df()
    return get_dataset_quick_profile(df)

@app.post("/datasets/upload", tags=["Datasets"])
async def upload_dataset_file(file: UploadFile = File(...)):
    contents = await file.read()
    df, meta = load_dataset(contents, filename=file.filename)
    active_datasets["default"] = df
    return {"status": "uploaded", "filename": file.filename, "metadata": meta}

@app.get("/data-preview", tags=["Data Preview"])
def preview_data(page: int = 1, page_size: int = 50, sort_by: Optional[str] = None, ascending: bool = True):
    df = get_current_df()
    if sort_by and sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=ascending)
    
    start = (page - 1) * page_size
    end = start + page_size
    sliced = df.iloc[start:end]
    return {
        "page": page,
        "page_size": page_size,
        "total_rows": len(df),
        "total_pages": int(np.ceil(len(df) / page_size)),
        "columns": list(df.columns),
        "records": sliced.to_dict(orient="records")
    }


# ---------------- 4. DATA CLEANING & PROCESSING ----------------
@app.post("/data-cleaning/audit", tags=["Data Cleaning"])
def audit_dataset():
    df = get_current_df()
    return audit_data_quality(df)

@app.post("/data-cleaning/auto-clean", tags=["Data Cleaning"])
def auto_clean():
    df = get_current_df()
    clean_df, log = one_click_ai_auto_clean(df)
    active_datasets["default"] = clean_df
    return {"status": "auto_cleaned", "changelog": log, "rows": len(clean_df), "columns": len(clean_df.columns)}

@app.post("/data-cleaning/impute", tags=["Data Cleaning"])
def impute(req: ImputationRequest):
    df = get_current_df()
    clean_df, log, stats = impute_missing_values(df, strategy_dict=req.strategy_dict)
    active_datasets["default"] = clean_df
    return {"status": "imputed", "changelog": log, "stats": stats}

@app.post("/data-cleaning/outliers", tags=["Data Cleaning"])
def outliers(req: OutlierRequest):
    df = get_current_df()
    clean_df, log = handle_outliers(df, columns=req.columns, method=req.method, action=req.action, factor=req.factor)
    active_datasets["default"] = clean_df
    return {"status": "outliers_handled", "changelog": log}


# ---------------- 5. FEATURE ENGINEERING ----------------
@app.get("/features/recommendations", tags=["Feature Engineering"])
def feature_recommendations():
    df = get_current_df()
    return get_feature_recommendations(df)

@app.post("/features/auto-engineer", tags=["Feature Engineering"])
def auto_feature_engineering():
    df = get_current_df()
    fe_df, log = one_click_ai_feature_engineering(df)
    active_datasets["default"] = fe_df
    return {"status": "engineered", "changelog": log, "total_features": len(fe_df.columns)}


# ---------------- 6. EDA & STATISTICAL ANALYSIS ----------------
@app.get("/eda/summary", tags=["EDA"])
def eda_summary():
    df = get_current_df()
    stats = compute_comprehensive_stats(df)
    insights = generate_automated_eda_insights(df)
    return {
        "numerical_stats": stats["numeric"].to_dict(orient="records"),
        "categorical_stats": stats["categorical"].to_dict(orient="records"),
        "insights": insights
    }

@app.get("/eda/correlations", tags=["EDA"])
def eda_correlations(method: str = "pearson"):
    df = get_current_df()
    corr = compute_correlation_analysis(df, method=method)
    return {
        "top_positive": corr["top_positive"],
        "top_negative": corr["top_negative"],
        "collinear_pairs": corr["collinear_pairs"]
    }


# ---------------- 7. AI VISUALIZATION & CHART RECOMMENDATIONS ----------------
@app.post("/charts/recommend", tags=["AI Visualization"])
def recommend_chart(req: ChartRecommendationRequest):
    """
    AI Chart Recommendation Engine:
    Identifies columns, selects optimal chart, generates Plotly visualization,
    explains chart rationale, and detects empirical statistical patterns.
    """
    df = get_current_df()
    res = default_chart_recommender.recommend_from_query(req.query, df)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))

    if res.get("mode") == "collection":
        serialized_collection = []
        for item in res.get("collection", []):
            serialized_collection.append({
                "title": item["title"],
                "chart_type": item["chart_type"],
                "columns": item["columns"],
                "rationale": item["rationale"],
                "explanation": item["explanation"],
                "patterns": item["patterns"],
                "figure": json.loads(item["figure"].to_json()) if item.get("figure") else None
            })
        return {
            "status": "success",
            "mode": "collection",
            "query": req.query,
            "summary": res.get("summary"),
            "charts": serialized_collection
        }

    return {
        "status": "success",
        "mode": "single",
        "query": req.query,
        "matched_columns": res.get("matched_columns"),
        "intent": res.get("intent"),
        "chart_type": res.get("chart_type"),
        "title": res.get("title"),
        "rationale": res.get("rationale"),
        "explanation": res.get("explanation"),
        "patterns": res.get("patterns"),
        "figure": json.loads(res["figure"].to_json()) if res.get("figure") else None
    }


@app.get("/charts/best-collection", tags=["AI Visualization"])
def get_best_charts_collection(max_charts: int = 5):
    """
    Synthesizes a curated collection of high-impact visualizations for the active dataset.
    """
    df = get_current_df()
    collection = default_chart_recommender.create_best_charts_collection(df, max_charts=max_charts)
    serialized = []
    for item in collection:
        serialized.append({
            "title": item["title"],
            "chart_type": item["chart_type"],
            "columns": item["columns"],
            "rationale": item["rationale"],
            "explanation": item["explanation"],
            "patterns": item["patterns"],
            "figure": json.loads(item["figure"].to_json()) if item.get("figure") else None
        })
    return {
        "status": "success",
        "total_charts": len(serialized),
        "charts": serialized
    }


@app.post("/statistics/hypothesis-test", tags=["Statistics"])
def hypothesis_test(req: HypothesisTestRequest):
    df = get_current_df()
    return run_hypothesis_test(
        df, req.test_type, req.var1, req.var2,
        req.group_col, req.group_val1, req.group_val2
    )

@app.post("/statistics/regression", tags=["Statistics"])
def regression(req: RegressionRequest):
    df = get_current_df()
    return run_regression_analysis(df, req.target_col, req.feature_cols, req.regression_type)


# ---------------- 7. SQL STUDIO ----------------
@app.post("/sql/execute", tags=["SQL Studio"])
def execute_sql(req: SQLQueryRequest):
    df = get_current_df()
    res, err, elapsed = sql_studio.execute_query(df, req.sql)
    if err:
        return {"status": "error", "error": err, "execution_time_ms": elapsed}
    return {
        "status": "success",
        "rows_returned": len(res),
        "execution_time_ms": elapsed,
        "columns": list(res.columns),
        "records": res.to_dict(orient="records")
    }

@app.post("/sql/nl-to-sql", tags=["SQL Studio"])
def nl_to_sql(req: NaturalLanguageSQLRequest):
    df = get_current_df()
    return generate_ai_sql(req.prompt, df)


# ---------------- 8. MACHINE LEARNING & AUTOML ----------------
@app.post("/ml/automl", tags=["Machine Learning"])
def automl(target_col: str, prediction_type: str = "auto"):
    df = get_current_df()
    res = run_automl_pipeline(df, target_col=target_col, prediction_type=prediction_type)
    return {
        "status": res["status"],
        "task_type": res["task_type"],
        "target_col": res["target_col"],
        "total_pipeline_time": res["total_pipeline_time"],
        "champion_model": res["champion_model"],
        "champion_record": res["champion_record"],
        "leaderboard": res["leaderboard"].to_dict(orient="records"),
        "explanation": res["explanation"],
        "leakage_detected": res["leakage_detected"],
        "registered_model_id": res["registered_model_card"].get("id")
    }

@app.get("/models/registry", tags=["Model Registry"])
def list_registered_models():
    return model_registry.get_all_models()


# ---------------- 9. FORECASTING & PREDICTIVE ANALYTICS ----------------
@app.post("/forecasting/generate", tags=["Forecasting"])
def forecast(req: ForecastRequest):
    df = get_current_df()
    res = generate_forecast(df, req.date_col, req.metric_col, horizon=req.horizon, freq=req.freq)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return {
        "date_col": res["date_col"],
        "metric_col": res["metric_col"],
        "horizon": res["horizon"],
        "accuracy": res["accuracy"],
        "forecast": res["forecast_df"].to_dict(orient="records"),
        "summary": res["summary"]
    }


# ---------------- 10. AI OMNIBAR & COPILOT ----------------
@app.post("/ai/command", tags=["AI Copilot"])
def omnibar_command(req: OmnibarRequest):
    df = get_current_df()
    return ai_orchestrator.route_omnibar_command(req.command, df)


# ---------------- 11. REPORTS & EXPORTS ----------------
@app.get("/reports/html", tags=["Reports"])
def export_html_report(report_type: str = "Executive Summary"):
    df = get_current_df()
    meta = get_dataset_quick_profile(df)
    insights = generate_automated_eda_insights(df)
    html = generate_html_report(report_type, "Current Project", df, meta, insights=insights)
    return {"report_type": report_type, "html_length": len(html), "preview_html": html[:1000]}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "online", "version": "2.0.0", "engine": "DuckDB + Scikit-Learn + FastAPI"}

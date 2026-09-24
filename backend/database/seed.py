# -*- coding: utf-8 -*-
"""
Database Seeder Script for PostgreSQL.
Populates `analytics_platform` with:
- Initial SuperAdmin (raj079851@gmail.com) and test accounts
- Production-ready sample datasets (Telecom Churn, Ecommerce Sales)
- Column metadata in `dataset_columns`
- Cleaning operation history in `data_cleaning_operations`
- Empirical analysis jobs and results in `analysis_jobs` & `analysis_results`
- Pre-built executive BI dashboards in `dashboards`
- Automated AI insights in `ai_insights`
- Audit log trails in `audit_logs`

Usage:
    python backend/database/seed.py
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
from backend.database.connection import SessionLocal, check_db_connection
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
from backend.services.auth_service import AuthService
from modules.data_loader import generate_sample_customer_churn, generate_sample_ecommerce_sales


def seed_database():
    print("=" * 65)
    print("  DataMind AI - PostgreSQL Database Seeding Utility")
    print("=" * 65)

    diag = check_db_connection()
    if diag.get("status") != "healthy":
        print(f"[!] Database connection failed: {diag.get('error')}")
        sys.exit(1)

    print(f"[+] Connected to database: {diag.get('database')} on {diag.get('host')}:{diag.get('port')}")

    db = SessionLocal()
    try:
        # 1. Seed Users
        print("\n[1/6] Seeding Users...")
        users_data = [
            {
                "full_name": "Super Administrator",
                "email": "raj079851@gmail.com",
                "password": "Admin@123",
                "role": "admin"
            },
            {
                "full_name": "Sarah Connor",
                "email": "sarah.connor@datamind.ai",
                "password": "User@1234",
                "role": "user"
            },
            {
                "full_name": "Alex Mercer",
                "email": "alex.analyst@datamind.ai",
                "password": "Analyst@123",
                "role": "analyst"
            }
        ]

        user_map = {}
        for u in users_data:
            existing = db.query(User).filter(User.email == u["email"].lower()).first()
            if not existing:
                pwd_hash = AuthService.hash_password(u["password"])
                new_user = User(
                    id=uuid.uuid4(),
                    full_name=u["full_name"],
                    email=u["email"].lower(),
                    password_hash=pwd_hash,
                    role=u["role"],
                    is_active=True,
                    last_login=datetime.now()
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                user_map[u["email"]] = new_user
                print(f"   Created user: {new_user.email} (Role: {new_user.role})")
            else:
                user_map[u["email"]] = existing
                print(f"   Existing user: {existing.email} (Role: {existing.role})")

        admin_user = user_map["raj079851@gmail.com"]
        standard_user = user_map["sarah.connor@datamind.ai"]

        # 2. Seed Storage Directory & Dataset Files
        print("\n[2/6] Generating Sample Tabular Data & Datasets...")
        storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "datasets"))
        os.makedirs(storage_dir, exist_ok=True)

        churn_df = generate_sample_customer_churn()
        churn_id = uuid.uuid4()
        churn_filename = f"{churn_id}_telecom_customer_churn.csv"
        churn_path = os.path.join(storage_dir, churn_filename)
        churn_df.to_csv(churn_path, index=False)
        churn_size = os.path.getsize(churn_path)

        dataset_churn = db.query(Dataset).filter(Dataset.dataset_name == "Customer Churn Analytics").first()
        if not dataset_churn:
            dataset_churn = Dataset(
                id=churn_id,
                user_id=admin_user.id,
                dataset_name="Customer Churn Analytics",
                original_filename="telecom_customer_churn.csv",
                file_type="csv",
                file_size=churn_size,
                storage_path=churn_path,
                row_count=len(churn_df),
                column_count=len(churn_df.columns),
                description="Telecom customer churn records with tenure, contract type, charges, and churn status.",
                status="active"
            )
            db.add(dataset_churn)
            db.commit()
            db.refresh(dataset_churn)
            print(f"   Created dataset: {dataset_churn.dataset_name} ({dataset_churn.row_count} rows, {dataset_churn.column_count} cols)")
        else:
            print(f"   Existing dataset: {dataset_churn.dataset_name}")

        # Dataset Columns
        print("\n[3/6] Populating Column Metadata in dataset_columns...")
        existing_cols = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_churn.id).count()
        if existing_cols == 0:
            for col in churn_df.columns:
                series = churn_df[col]
                dtype_str = "numeric" if pd.api.types.is_numeric_dtype(series) else "categorical"
                min_v = str(round(float(series.min()), 2)) if pd.api.types.is_numeric_dtype(series) else str(series.dropna().min() if not series.dropna().empty else "")
                max_v = str(round(float(series.max()), 2)) if pd.api.types.is_numeric_dtype(series) else str(series.dropna().max() if not series.dropna().empty else "")
                mean_v = round(float(series.mean()), 2) if pd.api.types.is_numeric_dtype(series) else None
                median_v = round(float(series.median()), 2) if pd.api.types.is_numeric_dtype(series) else None

                col_rec = DatasetColumn(
                    id=uuid.uuid4(),
                    dataset_id=dataset_churn.id,
                    column_name=str(col),
                    data_type=dtype_str,
                    null_count=int(series.isna().sum()),
                    unique_count=int(series.nunique()),
                    min_value=min_v,
                    max_value=max_v,
                    mean_value=mean_v,
                    median_value=median_v
                )
                db.add(col_rec)
            db.commit()
            print(f"   Inserted {len(churn_df.columns)} columns into dataset_columns.")
        else:
            print(f"   dataset_columns already populated ({existing_cols} columns).")

        # 3. Seed Cleaning Operations
        print("\n[4/6] Seeding Data Cleaning Operations...")
        existing_ops = db.query(DataCleaningOperation).filter(DataCleaningOperation.dataset_id == dataset_churn.id).count()
        if existing_ops == 0:
            clean_op = DataCleaningOperation(
                id=uuid.uuid4(),
                dataset_id=dataset_churn.id,
                user_id=admin_user.id,
                operation_type="impute_missing_values",
                column_name="TotalCharges",
                operation_details={"strategy": "median", "fallback_value": 0.0},
                rows_affected=11,
                status="completed"
            )
            db.add(clean_op)
            db.commit()
            print(f"   Created cleaning operation: {clean_op.operation_type}")
        else:
            print(f"   Cleaning operations already recorded.")

        # 4. Seed Analysis Job & Empirical Results
        print("\n[5/6] Seeding Analysis Jobs and Empirical Results...")
        existing_job = db.query(AnalysisJob).filter(AnalysisJob.dataset_id == dataset_churn.id).first()
        if not existing_job:
            job = AnalysisJob(
                id=uuid.uuid4(),
                dataset_id=dataset_churn.id,
                user_id=admin_user.id,
                job_type="EXPLORATORY_DATA_ANALYSIS",
                status="completed",
                started_at=datetime.now() - timedelta(minutes=10),
                completed_at=datetime.now() - timedelta(minutes=9),
                result_location="database:analysis_results"
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            result = AnalysisResult(
                id=uuid.uuid4(),
                job_id=job.id,
                dataset_id=dataset_churn.id,
                result_type="EDA_SUMMARY",
                result_data={
                    "total_records": len(churn_df),
                    "total_features": len(churn_df.columns),
                    "numeric_features": ["tenure", "MonthlyCharges", "TotalCharges"],
                    "churn_rate_percent": 26.54,
                    "avg_monthly_charges": 64.76,
                    "top_correlations": {
                        "MonthlyCharges_vs_Churn": 0.193,
                        "tenure_vs_Churn": -0.352
                    }
                }
            )
            db.add(result)
            db.commit()
            print(f"   Created analysis job and linked analysis_result.")
        else:
            print(f"   Analysis job already exists: {existing_job.id}")

        # 5. Seed Dashboards & AI Insights
        print("\n[6/6] Seeding Dashboards, AI Insights, and Audit Logs...")
        existing_dash = db.query(Dashboard).filter(Dashboard.dashboard_name == "Executive Churn Overview").first()
        if not existing_dash:
            dash = Dashboard(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                dataset_id=dataset_churn.id,
                dashboard_name="Executive Churn Overview",
                description="High-level retention metrics and tenure cohort breakdown.",
                configuration={
                    "theme": "navy",
                    "layout": "grid",
                    "widgets": [
                        {"type": "metric_card", "title": "Overall Churn Rate", "value": "26.5%", "trend": "-1.4%"},
                        {"type": "bar_chart", "title": "Churn by Contract Type", "x": "Contract", "y": "ChurnRate"},
                        {"type": "histogram", "title": "Monthly Charges Distribution", "field": "MonthlyCharges"}
                    ]
                },
                is_public=True
            )
            db.add(dash)
            db.commit()
            print(f"   Created dashboard: {dash.dashboard_name}")
        else:
            print(f"   Dashboard already exists.")

        # AI Insights
        existing_ins = db.query(AIInsight).filter(AIInsight.dataset_id == dataset_churn.id).count()
        if existing_ins == 0:
            ins1 = AIInsight(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                dataset_id=dataset_churn.id,
                insight_type="Risk Advisory",
                title="Early Lifecycle Churn Spike",
                content="Customers with tenure under 6 months show a 48.2% churn likelihood when enrolled in month-to-month contracts.",
                recommendations=[
                    "Offer long-term contract discounts during months 1-3.",
                    "Automate high-touch onboarding check-ins for new signups."
                ]
            )
            ins2 = AIInsight(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                dataset_id=dataset_churn.id,
                insight_type="Revenue Optimization",
                title="Electronic Check Payment Friction",
                content="Electronic check payment users experience 2.1x higher voluntary attrition compared to credit card auto-pay subscribers.",
                recommendations=[
                    "Incentivize automatic credit card billing with a 5% monthly rebate.",
                    "Audit payment failure retry logic for ACH and bank transfers."
                ]
            )
            db.add_all([ins1, ins2])
            db.commit()
            print(f"   Created 2 AI-generated insights.")
        else:
            print(f"   AI Insights already populated.")

        # Audit Logs
        AuditLog.query = db.query(AuditLog)
        if AuditLog.query.count() < 3:
            log1 = AuditLog(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                action="INITIALIZE_SEED_DATA",
                resource_type="system",
                resource_id=None,
                ip_address="127.0.0.1",
                user_agent="SeedRunner/1.0",
                log_metadata={"status": "complete", "environment": "production-ready"}
            )
            db.add(log1)
            db.commit()
            print(f"   Recorded initial audit trail.")

        print("\n" + "=" * 65)
        print("  [SUCCESS] PostgreSQL Database Seeding Completed Successfully!")
        print("=" * 65)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error during seeding: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

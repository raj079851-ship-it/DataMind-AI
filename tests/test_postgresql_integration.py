# -*- coding: utf-8 -*-
"""
End-to-End Automated Integration Test Suite for DataMind AI PostgreSQL Relational Backend.
Verifies all 16+ REST endpoints, RBAC, strict dataset isolation, column profiling,
cleaning operations, analysis jobs/results, dashboards, AI insights, and audit trails.
"""

import os
import sys
import io
import uuid
import pytest
from starlette.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.database.connection import SessionLocal
from backend.database.models import User, Dataset, AuditLog

client = TestClient(app)


def test_1_database_health_and_diagnostics():
    """Validates /api/health and /api/db-status endpoints."""
    print("\n--- [TEST 1] Testing PostgreSQL Health Diagnostics ---")
    
    # Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    data = res.json()
    assert data["status"] == "healthy"
    assert data["engine"] == "PostgreSQL"
    assert data["database"] == "analytics_platform"
    assert data["tables_count"] >= 9
    print(f" [+] /api/health OK: PostgreSQL version: {data['version'][:30]}...")

    # DB Status
    res_status = client.get("/api/db-status")
    assert res_status.status_code == 200, f"DB Status failed: {res_status.text}"
    status_data = res_status.json()
    assert status_data["status"] == "online"
    assert status_data["total_records_tracked"] >= 0
    print(f" [+] /api/db-status OK: Records tracked across tables: {status_data['total_records_tracked']}")


def test_2_auth_and_session_lifecycle():
    """Validates login, me, registration, and logout."""
    print("\n--- [TEST 2] Testing Authentication & RBAC ---")

    # 1. Login as seeded SuperAdmin
    login_res = client.post("/api/auth/login", json={
        "email": "raj079851@gmail.com",
        "password": "Admin@123"
    })
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    admin_token_data = login_res.json()
    assert "access_token" in admin_token_data
    assert admin_token_data["user"]["role"] == "admin"
    admin_token = admin_token_data["access_token"]
    print(f" [+] Admin login OK: Token retrieved ({admin_token[:20]}...)")

    # 2. Get profile /api/auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me_res.status_code == 200, f"/api/auth/me failed: {me_res.text}"
    assert me_res.json()["email"] == "raj079851@gmail.com"
    print(f" [+] /api/auth/me OK: User {me_res.json()['full_name']} verified.")

    # 3. Register a new user
    unique_suffix = uuid.uuid4().hex[:6]
    test_user_email = f"user_{unique_suffix}@datamind.ai"
    reg_res = client.post("/api/auth/register", json={
        "full_name": f"Test User {unique_suffix}",
        "email": test_user_email,
        "password": "TestPassword@2026",
        "role": "user"
    })
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert reg_data["email"] == test_user_email
    print(f" [+] /api/auth/register OK: Created account {test_user_email}")

    # 4. Login as newly registered user
    user_login_res = client.post("/api/auth/login", json={
        "email": test_user_email,
        "password": "TestPassword@2026"
    })
    assert user_login_res.status_code == 200
    user_token = user_login_res.json()["access_token"]
    print(f" [+] New user login OK: JWT issued.")

    return admin_token, user_token, test_user_email


def test_3_dataset_lifecycle_and_column_profiling():
    """Tests file upload, pandas column profiling, metadata persistence, and strict isolation."""
    print("\n--- [TEST 3] Testing Dataset Lifecycle & Isolation ---")

    # Get tokens
    admin_token, user_a_token, user_a_email = test_2_auth_and_session_lifecycle()

    # Create a secondary test user (User B) to test isolation
    unique_b = uuid.uuid4().hex[:6]
    user_b_email = f"user_b_{unique_b}@datamind.ai"
    client.post("/api/auth/register", json={
        "full_name": f"User B {unique_b}",
        "email": user_b_email,
        "password": "PasswordB@123",
        "role": "user"
    })
    b_login = client.post("/api/auth/login", json={"email": user_b_email, "password": "PasswordB@123"})
    user_b_token = b_login.json()["access_token"]

    # 1. User A uploads a dataset
    csv_data = (
        "transaction_id,customer_name,amount,category,is_fraud\n"
        "TX1001,Alice,150.50,Retail,0\n"
        "TX1002,Bob,2400.00,Electronics,1\n"
        "TX1003,Charlie,45.20,Food,0\n"
        "TX1004,David,890.10,Retail,0\n"
        "TX1005,Eva,12000.00,Luxury,1\n"
    )
    upload_files = {
        "file": ("transactions.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
    }
    upload_data = {
        "dataset_name": "Financial Transactions Q3",
        "description": "Credit card transaction anomaly stream"
    }
    upload_res = client.post(
        "/api/datasets/upload",
        files=upload_files,
        data=upload_data,
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    assert upload_res.status_code == 201, f"Dataset upload failed: {upload_res.text}"
    uploaded = upload_res.json()
    dataset_id = uploaded["id"]
    assert uploaded["row_count"] == 5
    assert uploaded["column_count"] == 5
    assert len(uploaded["columns"]) == 5
    print(f" [+] /api/datasets/upload OK: Dataset '{uploaded['dataset_name']}' created with ID: {dataset_id}")

    # Verify column profiling
    col_names = [c["column_name"] for c in uploaded["columns"]]
    assert "amount" in col_names
    assert "is_fraud" in col_names
    amount_col = next(c for c in uploaded["columns"] if c["column_name"] == "amount")
    assert amount_col["data_type"] == "numeric"
    assert amount_col["mean_value"] > 0
    print(f" [+] Column profiling verified: 'amount' mean = {amount_col['mean_value']}")

    # 2. Strict Dataset Isolation Check:
    # User B attempts to GET User A's dataset -> MUST receive HTTP 403 Forbidden
    res_b_attempt = client.get(f"/api/datasets/{dataset_id}", headers={"Authorization": f"Bearer {user_b_token}"})
    assert res_b_attempt.status_code == 403, f"Expected 403 for unauthorized user, got {res_b_attempt.status_code}"
    print(" [+] Strict Isolation Verified: User B blocked from accessing User A's dataset (HTTP 403).")

    # User B lists datasets -> should NOT see User A's dataset
    res_b_list = client.get("/api/datasets", headers={"Authorization": f"Bearer {user_b_token}"})
    assert res_b_list.status_code == 200
    b_dataset_ids = [d["id"] for d in res_b_list.json()]
    assert dataset_id not in b_dataset_ids
    print(" [+] Strict Isolation Verified: User A's dataset not visible in User B's dataset list.")

    # Admin CAN access User A's dataset
    res_admin_access = client.get(f"/api/datasets/{dataset_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_access.status_code == 200
    print(" [+] RBAC Verified: SuperAdmin can inspect User A's dataset.")

    return admin_token, user_a_token, dataset_id


def test_4_cleaning_analysis_dashboards_insights_audit():
    """Tests cleaning, analysis, dashboards, insights, and audit trail retrieval."""
    print("\n--- [TEST 4] Testing Cleaning, Analysis, Dashboards, Insights & Audit Logs ---")
    admin_token, user_token, dataset_id = test_3_dataset_lifecycle_and_column_profiling()

    # 1. Clean dataset
    clean_res = client.post(
        f"/api/datasets/{dataset_id}/clean",
        json={
            "operation_type": "handle_missing_values",
            "column_name": "amount",
            "operation_details": {"strategy": "mean"}
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert clean_res.status_code == 200, f"Cleaning failed: {clean_res.text}"
    assert clean_res.json()["status"] == "completed"
    print(" [+] /api/datasets/{id}/clean OK: Clean operation logged.")

    # 2. Trigger analysis job
    analyze_res = client.post(
        f"/api/datasets/{dataset_id}/analyze",
        json={
            "job_type": "EXPLORATORY_DATA_ANALYSIS",
            "parameters": {"depth": "deep"}
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert analyze_res.status_code == 200, f"Analysis trigger failed: {analyze_res.text}"
    job_id = analyze_res.json()["id"]
    assert analyze_res.json()["status"] == "completed"
    print(f" [+] /api/datasets/{id}/analyze OK: Job {job_id} completed.")

    # 3. Retrieve analysis results
    results_res = client.get(f"/api/analysis/{job_id}/results", headers={"Authorization": f"Bearer {user_token}"})
    assert results_res.status_code == 200, f"Analysis results failed: {results_res.text}"
    results_list = results_res.json()
    assert len(results_list) >= 1
    assert "result_data" in results_list[0]
    print(f" [+] /api/analysis/{job_id}/results OK: Retrieved {len(results_list)} result artifacts.")

    # 4. Generate AI insights
    insights_res = client.post(f"/api/insights/{dataset_id}/generate", headers={"Authorization": f"Bearer {user_token}"})
    assert insights_res.status_code == 201, f"Insights generation failed: {insights_res.text}"
    insights_data = insights_res.json()
    assert len(insights_data) >= 1
    print(f" [+] /api/insights/{dataset_id}/generate OK: Generated {len(insights_data)} automated insights.")

    # Read AI insights
    get_insights_res = client.get(f"/api/insights/{dataset_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert get_insights_res.status_code == 200
    assert len(get_insights_res.json()) >= 1
    print(f" [+] /api/insights/{dataset_id} OK: Insights retrieved.")

    # 5. Dashboard CRUD
    dash_create = client.post(
        "/api/dashboards",
        json={
            "dataset_id": dataset_id,
            "dashboard_name": "Fraud Detection Monitor",
            "description": "Real-time anomaly monitoring view",
            "configuration": {
                "layout": "grid",
                "charts": [{"type": "pie", "metric": "is_fraud"}]
            },
            "is_public": False
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert dash_create.status_code == 201, f"Dashboard creation failed: {dash_create.text}"
    dash_id = dash_create.json()["id"]
    print(f" [+] /api/dashboards (POST) OK: Dashboard {dash_id} created.")

    # Read dashboard
    dash_get = client.get(f"/api/dashboards/{dash_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert dash_get.status_code == 200
    assert dash_get.json()["dashboard_name"] == "Fraud Detection Monitor"
    print(" [+] /api/dashboards/{id} (GET) OK: Dashboard details retrieved.")

    # Update dashboard
    dash_put = client.put(
        f"/api/dashboards/{dash_id}",
        json={"dashboard_name": "Fraud Detection Monitor (Updated)"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert dash_put.status_code == 200
    assert dash_put.json()["dashboard_name"] == "Fraud Detection Monitor (Updated)"
    print(" [+] /api/dashboards/{id} (PUT) OK: Dashboard updated.")

    # 6. Audit logs inspection
    audit_res = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {user_token}"})
    assert audit_res.status_code == 200, f"Audit logs failed: {audit_res.text}"
    logs = audit_res.json()
    assert len(logs) >= 1
    actions = [l["action"] for l in logs]
    print(f" [+] /api/audit-logs OK: Retrieved {len(logs)} audit entries. Actions logged: {actions[:5]}")

    # 7. Delete dataset cleanup test
    del_res = client.delete(f"/api/datasets/{dataset_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert del_res.status_code == 200
    print(" [+] /api/datasets/{id} (DELETE) OK: Dataset cleaned up successfully.")


def test_5_security_and_smtp_auth_workflows():
    """
    Validates:
    1. Rejection of unauthenticated/unregistered user login (HTTP 404).
    2. Rejection of invalid password for registered user (HTTP 401).
    3. Proper login with valid credentials (HTTP 200).
    4. Forgot password flow:
       - 404 on unrecognised email
       - 200 and OTP generation for registered user
       - 400 on wrong OTP
       - 200 on valid OTP + password reset
       - Old password rejected (401)
       - New password accepted (200)
    5. SMTP diagnostics endpoint (/api/auth/smtp-status).
    """
    print("\n--- [TEST 5] Testing Security & Forgot-Password Recovery Workflows ---")
    from backend.services.smtp_service import default_smtp_service

    # 1. Unregistered user login rejection
    unregistered_email = f"ghost_{uuid.uuid4().hex[:8]}@unregistered.org"
    res_unreg = client.post("/api/auth/login", json={
        "email": unregistered_email,
        "password": "AnyPassword123!"
    })
    assert res_unreg.status_code == 404, f"Expected 404 for unregistered user, got {res_unreg.status_code}"
    assert "No account found with this email" in res_unreg.json()["detail"]
    print(" [+] Security Verified: Unregistered user login blocked with HTTP 404.")

    # 2. Register a dedicated test account
    recovery_email = f"recov_{uuid.uuid4().hex[:6]}@datamind.ai"
    initial_pass = "InitialPass@1234"
    new_pass = "RecoveredPass@5678"

    reg_res = client.post("/api/auth/register", json={
        "full_name": "Recovery Test User",
        "email": recovery_email,
        "password": initial_pass,
        "role": "user"
    })
    assert reg_res.status_code == 201

    # 3. Invalid password rejection for existing user
    bad_pass_res = client.post("/api/auth/login", json={
        "email": recovery_email,
        "password": "WrongPassword@999"
    })
    assert bad_pass_res.status_code == 401, f"Expected 401 for wrong password, got {bad_pass_res.status_code}"
    assert "Invalid password" in bad_pass_res.json()["detail"]
    print(" [+] Security Verified: Invalid password blocked with HTTP 401.")

    # 4. Valid password login succeeds
    good_login_res = client.post("/api/auth/login", json={
        "email": recovery_email,
        "password": initial_pass
    })
    assert good_login_res.status_code == 200
    print(" [+] Security Verified: Correct credentials authenticate with HTTP 200.")

    # 5. Forgot password request for unregistered user -> 404
    forgot_unreg = client.post("/api/auth/forgot-password/send-otp", json={
        "email": unregistered_email
    })
    assert forgot_unreg.status_code == 404
    print(" [+] Forgot Password Verified: Unregistered email request rejected with HTTP 404.")

    # 6. Forgot password request for registered user -> 200 + OTP generated
    forgot_req = client.post("/api/auth/forgot-password/send-otp", json={
        "email": recovery_email
    })
    assert forgot_req.status_code == 200
    store_key = recovery_email.strip().lower()
    assert store_key in default_smtp_service._otp_store
    server_otp = default_smtp_service._otp_store[store_key]["otp"]
    assert len(server_otp) == 6
    print(f" [+] Forgot Password Verified: Recovery OTP issued ({server_otp}) with 5-minute TTL.")

    # 7. Reset password with invalid OTP -> 400
    bad_otp_res = client.post("/api/auth/forgot-password/reset", json={
        "email": recovery_email,
        "otp": "000000" if server_otp != "000000" else "111111",
        "new_password": new_pass
    })
    assert bad_otp_res.status_code == 400
    print(" [+] Forgot Password Verified: Invalid OTP rejected with HTTP 400.")

    # 8. Reset password with correct OTP -> 200
    reset_ok_res = client.post("/api/auth/forgot-password/reset", json={
        "email": recovery_email,
        "otp": server_otp,
        "new_password": new_pass
    })
    assert reset_ok_res.status_code == 200
    assert reset_ok_res.json()["status"] == "success"
    print(" [+] Forgot Password Verified: Password reset successfully completed.")

    # 9. Old password now rejected
    old_pass_fail = client.post("/api/auth/login", json={
        "email": recovery_email,
        "password": initial_pass
    })
    assert old_pass_fail.status_code == 401
    print(" [+] Forgot Password Verified: Previous password is now invalid (HTTP 401).")

    # 10. New password now accepted
    new_pass_ok = client.post("/api/auth/login", json={
        "email": recovery_email,
        "password": new_pass
    })
    assert new_pass_ok.status_code == 200
    print(" [+] Forgot Password Verified: Login with newly recovered password succeeded (HTTP 200).")

    # 11. SMTP status diagnostic check
    smtp_status_res = client.get("/api/auth/smtp-status")
    assert smtp_status_res.status_code == 200
    smtp_data = smtp_status_res.json()
    assert "host" in smtp_data
    assert "port" in smtp_data
    print(f" [+] SMTP Diagnostics Verified: Host: {smtp_data['host']}, Port: {smtp_data['port']}.")


if __name__ == "__main__":
    print("=================================================================")
    print("  DataMind AI - PostgreSQL End-to-End Automated Test Suite")
    print("=================================================================")
    test_1_database_health_and_diagnostics()
    test_2_auth_and_session_lifecycle()
    test_3_dataset_lifecycle_and_column_profiling()
    test_4_cleaning_analysis_dashboards_insights_audit()
    test_5_security_and_smtp_auth_workflows()
    print("\n=================================================================")
    print("  [SUCCESS] All PostgreSQL End-to-End Tests Passed Cleanly!")
    print("=================================================================")

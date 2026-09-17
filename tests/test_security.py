# -*- coding: utf-8 -*-
"""
Tests for DataMind AI Enterprise Security Subsystem
Verifies:
1. Authentication & PBKDF2 Password Hashing
2. Cryptographic Sessions & Revocation
3. Role-Based Access Control (RBAC) & Permissions
4. OAuth State & Provider Management
5. Multi-Tenant Dataset Isolation & Path Sanitization
6. Column-Level Symmetric Encryption (Fernet AES)
7. API Key Issuance, Hashing & Verification
8. Rate Limiting Sliding-Window Token Bucket
9. Structured Audit Logging
10. Credential Sanitizer
"""

import os
import shutil
import tempfile
import unittest
import pandas as pd
import numpy as np

from modules.security.auth import UserManager, User, hash_password, verify_password
from modules.security.sessions import SessionManager
from modules.security.rbac import Role, Permission, has_permission, check_permission_or_raise, get_user_permissions
from modules.security.oauth import OAuthManager
from modules.security.isolation import DatasetIsolationManager
from modules.security.encryption import ColumnEncryptor
from modules.security.api_keys import APIKeyManager
from modules.security.rate_limiter import RateLimiter
from modules.security.audit_logger import AuditLogger
from modules.security.sanitizer import CredentialSanitizer


class TestSecurityAuth(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.users_file = os.path.join(self.tmp_dir, "test_users.json")
        self.user_mgr = UserManager(storage_file=self.users_file)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_password_hashing_and_verification(self):
        pwd = "EnterpriseSecret#2026"
        hashed = hash_password(pwd)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword!", hashed))

    def test_preseeded_enterprise_users(self):
        user, err = self.user_mgr.authenticate("admin", "Admin@123")
        self.assertIsNotNone(user)
        self.assertIsNone(err)
        self.assertEqual(user.role, Role.ADMIN)

        analyst, err2 = self.user_mgr.authenticate("analyst", "Analyst@123")
        self.assertIsNotNone(analyst)
        self.assertEqual(analyst.role, Role.ANALYST)

    def test_user_lockout_after_failed_attempts(self):
        # 5 consecutive failed attempts lock the account
        for _ in range(5):
            u, err = self.user_mgr.authenticate("viewer", "WrongPass123!")
            self.assertIsNone(u)

        # 6th attempt should return locked error
        u, err = self.user_mgr.authenticate("viewer", "Viewer@123")
        self.assertIsNone(u)
        self.assertIn("locked", err.lower())

    def test_create_and_delete_user(self):
        new_user, err = self.user_mgr.create_user(
            username="data_scientist",
            password="SecurePassword@99",
            email="ds@enterprise.io",
            role=Role.ANALYST
        )
        self.assertIsNotNone(new_user)
        self.assertIsNone(err)

        auth_user, err_auth = self.user_mgr.authenticate("data_scientist", "SecurePassword@99")
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user.email, "ds@enterprise.io")

        # Delete user
        deleted = self.user_mgr.delete_user(new_user.user_id)
        self.assertTrue(deleted)
        auth_after_del, _ = self.user_mgr.authenticate("data_scientist", "SecurePassword@99")
        self.assertIsNone(auth_after_del)


class TestSecuritySessions(unittest.TestCase):
    def setUp(self):
        self.session_mgr = SessionManager(secret_key="unit-test-secret-key-12345", ttl_seconds=3600)

    def test_create_and_validate_session(self):
        token = self.session_mgr.create_session("u_100", Role.ADMIN, "alice")
        self.assertIsInstance(token, str)
        self.assertTrue(token.startswith("dms_"))

        valid, session_data = self.session_mgr.validate_session(token)
        self.assertTrue(valid)
        self.assertIsNotNone(session_data)
        self.assertEqual(session_data["user_id"], "u_100")
        self.assertEqual(session_data["username"], "alice")
        self.assertEqual(session_data["role"], "Admin")

    def test_revocation_blacklist(self):
        token = self.session_mgr.create_session("u_200", Role.VIEWER, "bob")
        valid, _ = self.session_mgr.validate_session(token)
        self.assertTrue(valid)

        # Revoke session
        self.session_mgr.revoke_session(token)
        valid_after, _ = self.session_mgr.validate_session(token)
        self.assertFalse(valid_after)

    def test_tampered_token_fails(self):
        token = self.session_mgr.create_session("u_300", Role.ANALYST, "charlie")
        tampered = token[:-4] + "xxxx"
        valid, _ = self.session_mgr.validate_session(tampered)
        self.assertFalse(valid)


class TestSecurityRBAC(unittest.TestCase):
    def test_admin_has_all_permissions(self):
        self.assertTrue(has_permission(Role.ADMIN, Permission.EXECUTE_CODE))
        self.assertTrue(has_permission(Role.ADMIN, Permission.MANAGE_SECURITY))
        self.assertTrue(has_permission(Role.ADMIN, Permission.TRAIN_MODELS))
        self.assertTrue(has_permission(Role.ADMIN, Permission.CONNECT_DATABASE))

    def test_viewer_has_limited_permissions(self):
        self.assertTrue(has_permission(Role.VIEWER, Permission.VIEW_DASHBOARD))
        self.assertFalse(has_permission(Role.VIEWER, Permission.EXPORT_DATA))
        self.assertFalse(has_permission(Role.VIEWER, Permission.EXECUTE_CODE))
        self.assertFalse(has_permission(Role.VIEWER, Permission.MANAGE_SECURITY))
        self.assertFalse(has_permission(Role.VIEWER, Permission.CLEAN_DATA))

    def test_check_permission_or_raise(self):
        # Should not raise for admin
        try:
            check_permission_or_raise(Role.ADMIN, Permission.MANAGE_SECURITY)
        except PermissionError:
            self.fail("check_permission_or_raise unexpectedly raised PermissionError for Admin")

        # Should raise for viewer
        with self.assertRaises(PermissionError):
            check_permission_or_raise(Role.VIEWER, Permission.EXECUTE_CODE)


class TestSecurityOAuth(unittest.TestCase):
    def setUp(self):
        self.oauth_mgr = OAuthManager()

    def test_auth_url_generation(self):
        url, state = self.oauth_mgr.get_auth_url("google")
        self.assertIn("accounts.google.com", url)
        self.assertIn(state, url)

        url_gh, state_gh = self.oauth_mgr.get_auth_url("github")
        self.assertIn("github.com/login/oauth/authorize", url_gh)

    def test_oauth_sandbox_callback(self):
        _, state = self.oauth_mgr.get_auth_url("google")
        user_info, err = self.oauth_mgr.handle_sandbox_login("google", state, "testuser@company.com", "Test User")
        self.assertIsNone(err)
        self.assertIsNotNone(user_info)
        self.assertEqual(user_info["email"], "testuser@company.com")
        self.assertEqual(user_info["provider"], "google")


class TestSecurityIsolation(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.iso_mgr = DatasetIsolationManager(base_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_tenant_workspace_isolation(self):
        tenant_a_dir = self.iso_mgr.get_tenant_workspace("tenant_alpha")
        tenant_b_dir = self.iso_mgr.get_tenant_workspace("tenant_beta")

        self.assertNotEqual(tenant_a_dir, tenant_b_dir)
        self.assertTrue(os.path.exists(tenant_a_dir))
        self.assertTrue(os.path.exists(tenant_b_dir))

    def test_path_traversal_prevention(self):
        # Attack with path traversal attempt
        with self.assertRaises(ValueError):
            self.iso_mgr.resolve_safe_path("tenant_alpha", "../../etc/passwd")

        with self.assertRaises(ValueError):
            self.iso_mgr.resolve_safe_path("tenant_alpha", "..\\..\\windows\\system32\\cmd.exe")

    def test_safe_file_save_and_read(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        safe_path = self.iso_mgr.resolve_safe_path("tenant_alpha", "my_data.csv")
        df.to_csv(safe_path, index=False)

        read_df = pd.read_csv(safe_path)
        self.assertEqual(len(read_df), 3)


class TestSecurityEncryption(unittest.TestCase):
    def setUp(self):
        self.encryptor = ColumnEncryptor(secret_key="unit-test-master-encryption-key")

    def test_column_encryption_and_decryption(self):
        df = pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie"],
            "ssn": ["000-11-2222", "111-22-3333", "222-33-4444"],
            "salary": [95000, 120000, 85000]
        })

        enc_df, err = self.encryptor.encrypt_columns(df, ["ssn", "salary"])
        self.assertIsNone(err)
        # Encrypted values should not match original values
        self.assertNotEqual(str(enc_df["ssn"].iloc[0]), "000-11-2222")
        self.assertNotEqual(str(enc_df["salary"].iloc[0]), "95000")
        # Name column should remain untouched
        self.assertEqual(enc_df["name"].iloc[0], "Alice")

        # Decrypt back
        dec_df, err_dec = self.encryptor.decrypt_columns(enc_df, ["ssn", "salary"])
        self.assertIsNone(err_dec)
        self.assertEqual(dec_df["ssn"].iloc[0], "000-11-2222")
        self.assertEqual(str(dec_df["salary"].iloc[0]), "95000")


class TestSecurityAPIKeys(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.keys_file = os.path.join(self.tmp_dir, "test_api_keys.json")
        self.api_key_mgr = APIKeyManager(storage_file=self.keys_file)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_generate_and_validate_api_key(self):
        raw_key, meta = self.api_key_mgr.generate_api_key(
            name="Production CI Pipeline",
            role=Role.ADMIN,
            tenant_id="tenant_main",
            permissions=["read:all", "write:all"]
        )
        self.assertTrue(raw_key.startswith("dma_live_"))
        self.assertIsNotNone(meta)

        # Validate key
        is_valid, record = self.api_key_mgr.validate_api_key(raw_key)
        self.assertTrue(is_valid)
        self.assertEqual(record["name"], "Production CI Pipeline")
        self.assertEqual(record["role"], "Admin")

        # Invalid key fails
        is_valid_fake, _ = self.api_key_mgr.validate_api_key("dma_live_invalidkey1234567890")
        self.assertFalse(is_valid_fake)

    def test_revoke_api_key(self):
        raw_key, meta = self.api_key_mgr.generate_api_key("Short Lived Key")
        is_valid, _ = self.api_key_mgr.validate_api_key(raw_key)
        self.assertTrue(is_valid)

        # Revoke
        revoked = self.api_key_mgr.revoke_api_key(meta["key_id"])
        self.assertTrue(revoked)

        is_valid_after, _ = self.api_key_mgr.validate_api_key(raw_key)
        self.assertFalse(is_valid_after)


class TestSecurityRateLimiter(unittest.TestCase):
    def test_rate_limiter_allows_under_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        client_ip = "192.168.1.50"
        for _ in range(5):
            self.assertTrue(limiter.is_allowed(client_ip))

        # 6th request is throttled
        self.assertFalse(limiter.is_allowed(client_ip))

    def test_rate_limiter_isolated_by_client(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        self.assertTrue(limiter.is_allowed("client_A"))
        self.assertTrue(limiter.is_allowed("client_A"))
        self.assertFalse(limiter.is_allowed("client_A"))

        # Client B is unaffected
        self.assertTrue(limiter.is_allowed("client_B"))


class TestSecurityAuditLogger(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmp_dir, "test_audit.jsonl")
        self.logger = AuditLogger(log_file=self.log_file)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_log_event_and_retrieve(self):
        self.logger.log(
            user="admin",
            action="LOGIN_SUCCESS",
            resource="AUTH",
            status="SUCCESS",
            details={"method": "password", "ip": "127.0.0.1"}
        )
        self.logger.log(
            user="analyst",
            action="EXPORT_DATA",
            resource="DATASET_HOUSING",
            status="SUCCESS",
            details={"rows": 500, "format": "csv"}
        )

        entries = self.logger.get_logs(limit=10)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["action"], "EXPORT_DATA")
        self.assertEqual(entries[1]["action"], "LOGIN_SUCCESS")


class TestCredentialSanitizer(unittest.TestCase):
    def test_sanitizes_nested_dict(self):
        payload = {
            "model_name": "RandomForest",
            "api_key": "dma_live_99887766554433221100",
            "db_config": {
                "host": "localhost",
                "password": "SuperSecretPassword123!",
                "username": "root"
            },
            "token": "dms_abc.def",
            "score": 0.98
        }
        sanitized = CredentialSanitizer.sanitize(payload)
        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertEqual(sanitized["db_config"]["password"], "[REDACTED]")
        self.assertEqual(sanitized["token"], "[REDACTED]")
        self.assertEqual(sanitized["score"], 0.98)
        self.assertEqual(sanitized["model_name"], "RandomForest")


if __name__ == "__main__":
    unittest.main()

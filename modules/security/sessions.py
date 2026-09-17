# -*- coding: utf-8 -*-
"""
Secure Session Management Module
- Cryptographically signed HMAC-SHA256 session tokens
- Timestamped expiration (TTL) and sliding window session renewal
- Session revocation / token blacklisting for instant logout
- Tamper-proof payload verification
"""

import hmac
import time
import json
import base64
import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple, Union


SECRET_KEY = secrets.token_bytes(32)
DEFAULT_SESSION_TTL = 8 * 3600  # 8 hours


class SessionManager:
    """Issues, verifies, and revokes signed session tokens."""

    def __init__(
        self,
        secret: Optional[bytes] = None,
        ttl_seconds: int = DEFAULT_SESSION_TTL,
        secret_key: Optional[Any] = None
    ):
        if secret_key is not None:
            if isinstance(secret_key, str):
                self.secret = secret_key.encode("utf-8")
            else:
                self.secret = bytes(secret_key)
        else:
            self.secret = secret or SECRET_KEY
        self.ttl_seconds = ttl_seconds
        self.revoked_tokens = set()

    def create_session(
        self,
        username: str,
        role: Any,
        user_id_or_name: Optional[str] = None,
        tenant_id: str = "tenant_default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Issues a cryptographically signed, timestamped session token."""
        now = int(time.time())
        role_str = role.value if hasattr(role, "value") else str(role)
        sub_name = user_id_or_name or username
        user_id = username
        payload = {
            "sub": sub_name,
            "user_id": user_id,
            "username": sub_name,
            "role": role_str,
            "tenant_id": tenant_id,
            "iat": now,
            "exp": now + self.ttl_seconds,
            "nonce": secrets.token_hex(8),
            "meta": metadata or {}
        }
        raw_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
        sig = hmac.new(self.secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"dms_{payload_b64}.{sig}"

    def validate_session(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validates token and returns (is_valid, payload)."""
        try:
            payload = self.verify_session(token)
            return True, payload
        except Exception:
            return False, None

    def verify_session(self, token: str) -> Dict[str, Any]:
        """
        Validates token signature, expiration, and revocation status.
        Returns payload dict on success; raises ValueError on invalid/expired/tampered token.
        """
        if not token or not isinstance(token, str):
            raise ValueError("Session token missing.")

        if token in self.revoked_tokens:
            raise ValueError("Session has been revoked / logged out.")

        if not token.startswith("dms_") or "." not in token:
            raise ValueError("Malformed session token format.")

        parts = token[4:].split(".")
        if len(parts) != 2:
            raise ValueError("Invalid session token structure.")

        payload_b64, sig = parts[0], parts[1]

        # 1. Constant-time signature verification
        expected_sig = hmac.new(self.secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise ValueError("Tampered session token signature: access denied.")

        # 2. Decode payload
        try:
            # Re-pad base64
            padded = payload_b64 + "=" * (-len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(padded)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            raise ValueError("Failed to decode session payload.")

        # 3. Check expiration
        now = int(time.time())
        exp = payload.get("exp", 0)
        if now > exp:
            raise ValueError("Session has expired. Please log in again.")

        return payload

    def revoke_session(self, token: str):
        """Blacklists a session token upon user logout."""
        if token:
            self.revoked_tokens.add(token)

    def is_valid(self, token: str) -> bool:
        """Boolean check for token validity."""
        try:
            self.verify_session(token)
            return True
        except Exception:
            return False


# Global singleton
default_session_manager = SessionManager()

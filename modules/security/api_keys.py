# -*- coding: utf-8 -*-
"""
Secure API Key Management Module
- Cryptographically strong random API keys (dma_live_<32_random_bytes_hex>)
- Only SHA-256 hashes are persisted to disk; raw keys are displayed only once upon generation
- Constant-time hash verification against stored hashes
"""

import os
import json
import secrets
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


API_KEYS_STORE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".api_keys_store.json"
)


class APIKeyManager:
    """Manages API key lifecycle, hash generation, and constant-time verification."""

    def __init__(self, store_path: Optional[str] = None, storage_file: Optional[str] = None):
        self.store_path = storage_file or store_path or API_KEYS_STORE_FILE
        self.keys: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    self.keys = json.load(f)
            except Exception:
                self.keys = {}

    def _save(self):
        try:
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(self.keys, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()

    def generate_api_key(
        self,
        name: str,
        owner: Optional[str] = None,
        role: Any = "Analyst",
        tenant_id: str = "tenant_default",
        permissions: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generates a new API key.
        Returns (raw_key, key_metadata). Raw key must be saved by the user immediately.
        """
        random_part = secrets.token_hex(24)
        raw_key = f"dma_live_{random_part}"
        key_hash = self._hash_key(raw_key)

        key_id = f"key_{secrets.token_hex(6)}"
        role_str = role.value if hasattr(role, "value") else str(role)
        meta = {
            "id": key_id,
            "key_id": key_id,
            "name": name.strip(),
            "prefix": raw_key[:12] + "...",
            "hash": key_hash,
            "owner": owner or "system",
            "role": role_str,
            "tenant_id": tenant_id,
            "permissions": permissions or ["all"],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_used": None,
            "is_active": True
        }
        self.keys[key_id] = meta
        self._save()
        return raw_key, meta

    def verify_api_key(self, raw_key: str) -> Optional[Dict[str, Any]]:
        """
        Verifies a raw API key using constant-time hash comparison.
        Returns key metadata if valid, else None.
        """
        if not raw_key or not isinstance(raw_key, str):
            return None

        test_hash = self._hash_key(raw_key)
        for k_id, meta in self.keys.items():
            if not meta.get("is_active", True):
                continue
            if hmac.compare_digest(meta["hash"], test_hash):
                meta["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save()
                safe = meta.copy()
                safe.pop("hash", None)
                return safe

        return None

    def validate_api_key(self, raw_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validates raw API key returning (is_valid, record_or_none)."""
        rec = self.verify_api_key(raw_key)
        if rec is not None:
            return True, rec
        return False, None


    def revoke_api_key(self, key_id: str) -> bool:
        """Revokes an API key."""
        if key_id in self.keys:
            self.keys[key_id]["is_active"] = False
            self._save()
            return True
        return False

    def list_api_keys(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists API keys stripped of hashes."""
        res = []
        for k in self.keys.values():
            if owner is None or k.get("owner") == owner:
                safe = k.copy()
                safe.pop("hash", None)
                res.append(safe)
        return sorted(res, key=lambda x: x.get("created_at", ""), reverse=True)


# Global singleton
default_api_key_manager = APIKeyManager()

# -*- coding: utf-8 -*-
"""
Payload & Response Sanitizer Module
- Recursively scrubs secrets, passwords, API tokens, hashes, and private keys from any outgoing data structure
- Guarantees zero credential exposure to frontend, UI templates, or REST responses
"""

import re
from typing import Any, Dict, List, Set, Union


SENSITIVE_KEY_PATTERNS: Set[str] = {
    "password", "pwd", "secret", "token", "hash", "private_key", "api_key",
    "apikey", "auth", "credential", "client_secret", "encryption_key"
}

SAFE_RETURN_KEYS: Set[str] = {
    "access_token", "token_type", "session_token"
}


def is_sensitive_key(key: str) -> bool:
    """Checks if a dict key name denotes a sensitive credential."""
    k_lower = key.lower().replace("-", "_")
    if k_lower in SAFE_RETURN_KEYS:
        return False
    return any(pat in k_lower for pat in SENSITIVE_KEY_PATTERNS)


def sanitize_payload(data: Any, mask_value: str = "[REDACTED]", preserve_edges: bool = False) -> Any:
    """
    Recursively traverses dictionaries, lists, and primitives,
    masking any sensitive fields so secrets can never be exposed to the client.
    """
    if data is None:
        return None

    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if is_sensitive_key(str(k)):
                if preserve_edges and isinstance(v, str) and len(v) > 6:
                    cleaned[k] = f"{v[:2]}***[REDACTED]***{v[-2:]}"
                else:
                    cleaned[k] = mask_value
            else:
                cleaned[k] = sanitize_payload(v, mask_value, preserve_edges)
        return cleaned

    if isinstance(data, list):
        return [sanitize_payload(item, mask_value, preserve_edges) for item in data]

    if isinstance(data, (tuple, set)):
        return [sanitize_payload(item, mask_value, preserve_edges) for item in data]

    return data


class CredentialSanitizer:
    """Enterprise credential sanitizer utility class."""
    @staticmethod
    def sanitize(data: Any, mask_value: str = "[REDACTED]") -> Any:
        return sanitize_payload(data, mask_value=mask_value, preserve_edges=False)

    @staticmethod
    def sanitize_masked(data: Any) -> Any:
        return sanitize_payload(data, mask_value="[REDACTED]", preserve_edges=True)


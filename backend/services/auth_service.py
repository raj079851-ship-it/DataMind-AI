# -*- coding: utf-8 -*-
"""
Authentication and Cryptographic Security Service.
- Password hashing using bcrypt with 12 rounds
- Backward-compatible verification for legacy PBKDF2-HMAC-SHA256 hashes
- JWT access token generation and cryptographic payload verification
"""

import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import jwt, JWTError

from backend.database.models import User
from backend.database.repositories import UserRepository

# Configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET", "d8f9c2a1e4b76543210fedcba9876543210abcdef0123456789abcdef0123456")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes plaintext password using bcrypt with salt."""
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies plaintext against bcrypt or legacy PBKDF2 password hashes."""
        if not plain_password or not hashed_password:
            return False

        # 1. Standard bcrypt hash
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
            try:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False

        # 2. Legacy PBKDF2 fallback
        if hashed_password.startswith("pbkdf2_sha256$"):
            try:
                import hashlib, hmac
                parts = hashed_password.split("$")
                rounds = int(parts[1])
                salt = bytes.fromhex(parts[2])
                expected = bytes.fromhex(parts[3])
                actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, rounds)
                return hmac.compare_digest(actual, expected)
            except Exception:
                return False

        return False

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Generates cryptographically signed JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Decodes and validates signature and expiration of JWT access token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError:
            return None

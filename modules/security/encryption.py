# -*- coding: utf-8 -*-
"""
Data-at-Rest & Column-Level Encryption Module
- Encrypts sensitive tabular columns (e.g. SSN, Salary, Credit Card, Email) using AES-128/256 Fernet
- Reversible decryption for authorized roles
- Seamless integration with CredentialVault
"""

import pandas as pd
from typing import List, Optional
from modules.connectors.security import CredentialVault, default_vault


class ColumnEncryptor:
    """Encrypts and decrypts specific DataFrame columns containing sensitive PII."""

    def __init__(self, vault: Optional[CredentialVault] = None, secret_key: Optional[str] = None):
        if secret_key is not None:
            self.vault = CredentialVault(master_key=secret_key)
        else:
            self.vault = vault or default_vault

    def encrypt_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Encrypts all values in a specified column into ciphertext tokens."""
        if column not in df.columns:
            raise ValueError(f"Column '{column}' does not exist in DataFrame.")

        df_enc = df.copy()
        df_enc[column] = df_enc[column].apply(
            lambda v: self.vault.encrypt(str(v)) if pd.notna(v) and str(v).strip() != "" else v
        )
        return df_enc

    def encrypt_columns(self, df: pd.DataFrame, columns: List[str]):
        """Encrypts multiple columns and returns (df_enc, error)."""
        try:
            res = df.copy()
            for col in columns:
                if col in res.columns:
                    res = self.encrypt_column(res, col)
            return res, None
        except Exception as e:
            return df, str(e)

    def decrypt_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Decrypts an encrypted column back to plaintext."""
        if column not in df.columns:
            raise ValueError(f"Column '{column}' does not exist in DataFrame.")

        df_dec = df.copy()
        df_dec[column] = df_dec[column].apply(
            lambda v: self.vault.decrypt(str(v)) if pd.notna(v) and str(v).startswith("gAAAAA") else v
        )
        return df_dec

    def decrypt_columns(self, df: pd.DataFrame, columns: List[str]):
        """Decrypts multiple columns and returns (df_dec, error)."""
        try:
            res = df.copy()
            for col in columns:
                if col in res.columns:
                    res = self.decrypt_column(res, col)
            return res, None
        except Exception as e:
            return df, str(e)


    def is_encrypted_column(self, s: pd.Series) -> bool:
        """Checks if a column contains Fernet ciphertext tokens."""
        sample = s.dropna().head(5).astype(str)
        if len(sample) == 0:
            return False
        return (sample.str.startswith("gAAAAA")).all()


# Global singleton
default_column_encryptor = ColumnEncryptor()

# -*- coding: utf-8 -*-
"""
Enterprise SMTP Gateway Service.
Handles:
- Cryptographic OTP generation and server-side memory store with 5-minute TTL
- SMTP Email Dispatch with TLS / SSL support (Gmail, Outlook, custom SMTP relay)
- Branded responsive HTML verification email templates
- Diagnostics and live connection testing
- Dynamic runtime configuration and .env updates
"""

import os
import sys
import time
import hmac
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Tuple, Optional


class SMTPService:
    _instance = None
    _otp_store: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self.reload_config()

    def reload_config(self):
        """Loads SMTP settings from environment variables."""
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "").strip()
        self.password = os.getenv("SMTP_PASS", "").strip()
        self.sender = os.getenv("SMTP_SENDER", self.user or "security-gate@datamind.ai").strip()
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ["true", "1", "yes"]

    @classmethod
    def get_instance(cls) -> "SMTPService":
        if cls._instance is None:
            cls._instance = SMTPService()
        return cls._instance

    def get_status(self) -> Dict[str, Any]:
        """Returns non-sensitive configuration status for diagnostics and UI display."""
        is_configured = bool(self.host and self.user and self.password)
        masked_user = ""
        if self.user:
            parts = self.user.split("@")
            if len(parts) == 2:
                name, domain = parts
                masked_user = f"{name[:2]}***@{domain}"
            else:
                masked_user = f"{self.user[:3]}***"

        return {
            "host": self.host,
            "port": self.port,
            "sender": self.sender,
            "user_configured": bool(self.user),
            "user_masked": masked_user,
            "is_configured": is_configured,
            "use_tls": self.use_tls
        }

    def update_config(self, host: str, port: int, user: str, password: str, sender: str = None, use_tls: bool = True):
        """Updates runtime configuration and syncs with .env file."""
        self.host = host.strip()
        self.port = int(port)
        self.user = user.strip()
        if password:
            self.password = password.strip()
        self.sender = (sender or self.user or "security-gate@datamind.ai").strip()
        self.use_tls = use_tls

        # Update environment variables
        os.environ["SMTP_HOST"] = self.host
        os.environ["SMTP_PORT"] = str(self.port)
        os.environ["SMTP_USER"] = self.user
        if password:
            os.environ["SMTP_PASS"] = self.password
        os.environ["SMTP_SENDER"] = self.sender
        os.environ["SMTP_USE_TLS"] = "true" if self.use_tls else "false"

        # Update .env file if it exists
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()

                def update_or_append(txt, key, val):
                    import re
                    pattern = rf"^{key}=.*$"
                    if re.search(pattern, txt, flags=re.MULTILINE):
                        return re.sub(pattern, f"{key}={val}", txt, flags=re.MULTILINE)
                    else:
                        return txt + f"\n{key}={val}"

                content = update_or_append(content, "SMTP_HOST", self.host)
                content = update_or_append(content, "SMTP_PORT", str(self.port))
                content = update_or_append(content, "SMTP_USER", self.user)
                if password:
                    content = update_or_append(content, "SMTP_PASS", self.password)
                content = update_or_append(content, "SMTP_SENDER", self.sender)
                content = update_or_append(content, "SMTP_USE_TLS", "true" if self.use_tls else "false")

                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                print(f"[WARN] Could not write updated SMTP config to .env: {e}")

    def generate_otp(self) -> str:
        """Generates a cryptographically strong 6-digit numeric OTP."""
        return f"{secrets.randbelow(900000) + 100000}"

    def store_otp(self, email: str, otp: str, purpose: str = "login", ttl_seconds: int = 300):
        """Stores OTP in memory with a 5-minute expiration timestamp."""
        key = email.strip().lower()
        self._otp_store[key] = {
            "otp": otp,
            "purpose": purpose,
            "expires_at": time.time() + ttl_seconds,
            "created_at": time.time()
        }

    def verify_otp(self, email: str, entered_otp: str, purpose: str = "login") -> Tuple[bool, str]:
        """Validates the entered OTP code against server memory using constant-time comparison."""
        key = email.strip().lower()
        record = self._otp_store.get(key)
        if not record:
            return False, "No active OTP request found for this email. Please request a new code."

        if time.time() > record["expires_at"]:
            self._otp_store.pop(key, None)
            return False, "The OTP verification code has expired. Please request a new code."

        if record.get("purpose") != purpose:
            return False, "Invalid OTP purpose context."

        # Constant-time comparison to prevent timing attacks
        expected_otp = str(record["otp"]).strip()
        actual_otp = str(entered_otp).strip()

        if not hmac.compare_digest(expected_otp, actual_otp):
            return False, "Incorrect verification code. Please check your email and try again."

        # Burn OTP upon successful verification
        self._otp_store.pop(key, None)
        return True, "OTP verified successfully."

    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> Tuple[bool, str]:
        """Sends an email using standard SMTP with TLS or SSL."""
        if not self.host:
            return False, "SMTP Host is not configured."
        if not self.user or not self.password:
            return False, (
                "SMTP Credentials Missing: SMTP_USER and SMTP_PASS are not configured in .env. "
                "For Gmail, use your email and a 16-character Google App Password."
            )

        msg = MIMEMultipart("alternative")
        msg["From"] = f"DataMind AI Security Gate <{self.sender}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        part1 = MIMEText(body_text, "plain", "utf-8")
        msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, "html", "utf-8")
            msg.attach(part2)

        try:
            if self.port == 465:
                # SSL Direct
                with smtplib.SMTP_SSL(self.host, self.port, timeout=12) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.sender, [to_email], msg.as_string())
            else:
                # Standard STARTTLS (e.g. port 587)
                with smtplib.SMTP(self.host, self.port, timeout=12) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.user, self.password)
                    server.sendmail(self.sender, [to_email], msg.as_string())

            return True, f"Email delivered successfully to {to_email}"
        except smtplib.SMTPAuthenticationError as e:
            err = (
                f"SMTP Authentication Error ({e.smtp_code}): Invalid username or password. "
                "If using Gmail, please create a Google App Password at https://myaccount.google.com/apppasswords."
            )
            print(f"[ERROR] {err}")
            return False, err
        except smtplib.SMTPConnectError as e:
            err = f"SMTP Connection Error: Could not connect to {self.host}:{self.port}."
            print(f"[ERROR] {err}")
            return False, err
        except Exception as e:
            err = f"SMTP Transport Failure: {str(e)}"
            print(f"[ERROR] {err}")
            return False, err

    def dispatch_otp_email(self, to_email: str, otp: str, purpose_label: str = "Sign-In", full_name: str = "") -> Tuple[bool, str]:
        """Renders responsive template and dispatches OTP email."""
        display_name = full_name or to_email.split("@")[0]
        subject = f"DataMind AI Security Code: {otp} ({purpose_label})"

        body_text = f"""DataMind AI Enterprise Security Gate
--------------------------------------------------
Hello {display_name},

Your 6-digit verification code is: {otp}

This code is valid for 5 minutes.
Context: {purpose_label}

If you did not request this verification code, please ignore this email or contact security immediately.

DataMind AI Platform Security Team
"""

        body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>DataMind AI Verification Code</title>
</head>
<body style="margin:0; padding:0; background-color:#0b0f19; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color:#e2e8f0;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#0b0f19; padding:40px 10px;">
    <tr>
      <td align="center">
        <table width="100%" max-width="520" border="0" cellspacing="0" cellpadding="0" style="max-width:520px; background:#131c2e; border:1px solid #23334d; border-radius:14px; overflow:hidden; box-shadow:0 12px 30px rgba(0,0,0,0.5);">
          <!-- Header Banner -->
          <tr>
            <td style="background:linear-gradient(135deg, #0284c7 0%, #1e3a8a 100%); padding:24px 30px; text-align:center;">
              <div style="font-size:32px; margin-bottom:8px;">🛡️</div>
              <h1 style="color:#ffffff; margin:0; font-size:20px; font-weight:800; letter-spacing:0.5px;">DataMind AI Security Gate</h1>
              <p style="color:#93c5fd; margin:4px 0 0 0; font-size:12px; font-weight:500;">Authentication &amp; Account Protection</p>
            </td>
          </tr>
          <!-- Body Content -->
          <tr>
            <td style="padding:32px 30px;">
              <p style="font-size:15px; margin:0 0 16px 0; color:#f8fafc;">Hello <strong style="color:#38bdf8;">{display_name}</strong>,</p>
              <p style="font-size:13px; line-height:1.6; color:#94a3b8; margin:0 0 24px 0;">
                You recently requested a verification code for <strong>{purpose_label}</strong> on the DataMind AI Analytics Platform. Use the code below to complete your verification:
              </p>
              
              <!-- OTP Box -->
              <div style="background:#0b1324; border:1.5px dashed #0284c7; border-radius:10px; padding:18px; text-align:center; margin-bottom:24px;">
                <div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#38bdf8; font-weight:700; margin-bottom:8px;">Your 6-Digit One-Time Password</div>
                <div style="font-size:36px; font-weight:900; letter-spacing:8px; color:#ffffff; font-family:'Courier New', monospace;">{otp}</div>
                <div style="font-size:11px; color:#ef4444; margin-top:8px; font-weight:600;">⏱️ Code expires in 5 minutes</div>
              </div>

              <div style="background:rgba(239, 68, 68, 0.08); border-left:3px solid #ef4444; padding:10px 14px; border-radius:4px; font-size:11px; line-height:1.5; color:#cbd5e1; margin-bottom:20px;">
                <strong>Security Alert:</strong> Never share this code with anyone. DataMind AI support representatives will never ask you for your verification code.
              </div>

              <p style="font-size:11px; color:#64748b; margin:0; line-height:1.5;">
                If you did not initiate this request, someone may be attempting to access your account. Please log in immediately and update your password.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#0e1626; padding:16px 30px; text-align:center; border-top:1px solid #1e293b; font-size:11px; color:#64748b;">
              &copy; 2026 DataMind AI Enterprise &bull; Autonomous Machine Learning &amp; Analytics Platform
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return self.send_email(to_email, subject, body_text, body_html)


# Global singleton
default_smtp_service = SMTPService.get_instance()

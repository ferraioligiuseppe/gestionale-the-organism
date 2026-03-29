from __future__ import annotations
import secrets
from datetime import datetime, timedelta, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_capture_token(expire_minutes: int = 30) -> dict:
    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return {"token": token, "created_at": utc_now_iso(), "expires_at": expires_at.isoformat()}

def is_token_expired(expires_at: str) -> bool:
    try:
        exp = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) > exp
    except Exception:
        return True

"""Device tokens. A device gets a random token once, when it is registered.
Only its SHA-256 hash is stored, so a leaked database doesn't leak tokens."""
import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Device

# Reads "Authorization: Bearer <token>", and adds it to the Authorize button in /docs
bearer = HTTPBearer(auto_error=False, scheme_name="Device",
                    description="A mirror's token, from registering it")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Device:
    """FastAPI dependency: the device whose token is in "Authorization: Bearer <token>" """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing device token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    device = db.scalar(select(Device).where(Device.token_hash == hash_token(token)))
    if device is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Unknown device token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return device

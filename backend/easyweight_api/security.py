"""Device tokens. A device gets a random token once, when it is registered.
Only its SHA-256 hash is stored, so a leaked database doesn't leak tokens."""
import hashlib
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Device


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_device(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Device:
    """FastAPI dependency: the device whose token is in "Authorization: Bearer <token>" """
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
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

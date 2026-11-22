"""User accounts: passwords and login tokens.

Signing in gives two tokens:

    access token   short-lived (15 minutes). Sent with every request. A signed
                   JWT, so checking it needs no database lookup
    refresh token  long-lived (30 days). Only used to get a new pair. Each use
                   replaces it, and the server remembers which ones were used,
                   so a stolen refresh token gives itself away the moment both
                   the thief and the owner use it: then all of that user's
                   sign-ins are cancelled

Passwords are stored as Argon2 hashes, never as the password itself.
"""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import RefreshToken, User

ALGORITHM = "HS256"
_hasher = PasswordHasher()

# Reads "Authorization: Bearer <access token>". In /docs, its Authorize button
# signs in with email and password through the login endpoint
user_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False,
                                   scheme_name="User")

# Checked against when the email doesn't exist, so a wrong email takes as long
# as a wrong password and doesn't reveal which emails have accounts
_DUMMY_HASH = _hasher.hash("not a real password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return user if verify_password(password, user.password_hash) else None


def _encode(claims: dict, lifetime: timedelta) -> str:
    now = datetime.now(UTC)
    claims = {**claims, "iat": now, "exp": now + lifetime}
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=ALGORITHM)


def _decode(token: str, expected_type: str) -> dict:
    try:
        claims = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token") from None
    if claims.get("type") != expected_type:  # a refresh token can't be used to sign in
        raise _unauthorized("Wrong kind of token")
    return claims


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail,
                         headers={"WWW-Authenticate": "Bearer"})


def issue_tokens(db: Session, user: User) -> dict:
    """A new access and refresh token pair. Commits"""
    settings = get_settings()
    lifetime = timedelta(days=settings.refresh_token_days)
    stored = RefreshToken(user_id=user.id, expires_at=datetime.now(UTC) + lifetime)
    db.add(stored)
    db.commit()
    return {
        "access_token": _encode({"sub": str(user.id), "type": "access"},
                                timedelta(minutes=settings.access_token_minutes)),
        "refresh_token": _encode({"sub": str(user.id), "type": "refresh",
                                  "jti": str(stored.id)}, lifetime),
        "token_type": "bearer",
    }


def rotate_refresh_token(db: Session, token: str) -> dict:
    """Swap a refresh token for a new pair. Using one that was already used
    cancels every sign-in of that user"""
    claims = _decode(token, "refresh")
    stored = db.get(RefreshToken, uuid.UUID(claims["jti"]))
    if stored is None:
        raise _unauthorized("Unknown refresh token")
    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        db.execute(update(RefreshToken)
                   .where(RefreshToken.user_id == stored.user_id,
                          RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=now))
        db.commit()
        raise _unauthorized("Refresh token was already used. Please sign in again")
    stored.revoked_at = now
    return issue_tokens(db, db.get(User, stored.user_id))


def revoke_refresh_token(db: Session, token: str) -> None:
    try:
        claims = _decode(token, "refresh")
    except HTTPException:
        return  # signing out with a bad token: nothing to do
    # Deleted, not marked as used: using a signed-out token later (say, from
    # a stale browser tab) is then just "unknown", and doesn't count as theft
    db.execute(delete(RefreshToken).where(RefreshToken.id == uuid.UUID(claims["jti"]),
                                          RefreshToken.revoked_at.is_(None)))
    db.commit()


def access_claims(token: str) -> dict:
    """The claims of a valid access token ("sub" is the user's id). Raises 401"""
    return _decode(token, "access")


def current_user(token: str | None = Depends(user_bearer), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: the signed-in user"""
    if not token:
        raise _unauthorized("Not signed in")
    claims = access_claims(token)
    user = db.get(User, uuid.UUID(claims["sub"]))
    if user is None:
        raise _unauthorized("User no longer exists")
    return user

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import (
    authenticate,
    hash_password,
    issue_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from ..db import get_db
from ..models import User
from ..schemas import RefreshRequest, TokenPair, UserCreate

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    """Create an account. Signs in right away, so the answer is a token pair"""
    email = body.email.strip().lower()
    taken = HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    if db.scalar(select(User.id).where(User.email == email)):
        raise taken
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # someone registered the same email a moment ago
        db.rollback()
        raise taken from None
    return issue_tokens(db, user)


@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Sign in with email and password, sent as a form (the OAuth2 standard,
    which is what the Authorize button in /docs uses). The email goes in the
    `username` field"""
    user = authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Swap a refresh token for a new pair. Each refresh token works once"""
    return rotate_refresh_token(db, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    """Sign out: the refresh token stops working. The access token still works
    until it expires, at most 15 minutes"""
    revoke_refresh_token(db, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

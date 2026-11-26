from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..demo import demo_user
from ..models import User
from ..ratelimit import RateLimiter, client_address
from ..schemas import RefreshRequest, TokenPair, UserCreate
from ..user_auth import (
    authenticate,
    hash_password,
    issue_tokens,
    normalize_email,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_settings = get_settings()
login_limit = RateLimiter(_settings.login_attempts, _settings.login_window_seconds)
signup_limit = RateLimiter(_settings.signups_per_hour, 3600)


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Create an account. Signs in right away, so the answer is a token pair"""
    signup_limit.hit(client_address(request))
    email = normalize_email(body.email)
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
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    """Sign in with email and password, sent as a form (the OAuth2 standard,
    which is what the Authorize button in /docs uses). The email goes in the
    `username` field. After 10 wrong tries in 5 minutes: 429, wait a bit"""
    key = f"{client_address(request)}:{normalize_email(form.username)}"
    login_limit.hit(key)
    user = authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    login_limit.reset(key)
    return issue_tokens(db, user)


@router.post("/demo", response_model=TokenPair)
def demo(db: Session = Depends(get_db)):
    """Sign in to the read-only demo account: a made-up user with about two
    months of simulated workouts, kept up to date"""
    if not get_settings().demo_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "There is no demo here")
    return issue_tokens(db, demo_user(db))


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

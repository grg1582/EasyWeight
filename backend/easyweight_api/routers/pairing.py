"""Connecting a mirror by scanning a QR code, without typing a password on it.

1. The mirror makes its own random token and sends only its SHA-256 hash:
   POST /api/v1/pairing → a short code, e.g. "K7QM-3XPA", valid 10 minutes.
2. It shows the code as a QR code of <site>/pair/<code>. You scan it with your
   phone, where you're signed in, and confirm:
   POST /api/v1/pairing/{code}/claim → the device is created with that hash.
3. Meanwhile the mirror asks, with its token, whether it was claimed:
   GET /api/v1/pairing/{code} → "waiting", then "paired".

The token never leaves the mirror, and nothing on the server can turn the
hash back into it. A code is short enough to type, so claiming is rate limited.
"""
import re
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..demo import not_demo
from ..models import Device, Pairing, User
from ..ratelimit import RateLimiter, client_address
from ..schemas import PairingClaim, PairingCreate, PairingCreated, PairingStatus
from ..security import bearer, hash_token

router = APIRouter(prefix="/api/v1/pairing", tags=["pairing"])

LIFETIME = timedelta(minutes=10)
# No 0/O or 1/I/L, which look alike on a screen
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8

create_limit = RateLimiter(20, 3600)  # codes per address per hour
claim_limit = RateLimiter(10, 600)  # claims per user per 10 minutes: guessing codes is hopeless


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalize(code: str) -> str:
    """'k7qm-3xpa' or 'K7QM 3XPA' → 'K7QM3XPA'"""
    return re.sub(r"[\s-]", "", code).upper()


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "This code doesn't exist or has expired")


@router.post("", response_model=PairingCreated, status_code=status.HTTP_201_CREATED)
def start_pairing(body: PairingCreate, request: Request, db: Session = Depends(get_db)):
    """A mirror asks for a code to show as a QR code. It sends the SHA-256 hash
    of a token it made, never the token"""
    create_limit.hit(client_address(request))
    now = datetime.now(UTC)
    db.execute(delete(Pairing).where(Pairing.expires_at < now, Pairing.device_id.is_(None)))
    taken = db.scalar(select(Device.id).where(Device.token_hash == body.token_hash)) or db.scalar(
        select(Pairing.code).where(Pairing.token_hash == body.token_hash))
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "Make a new token")
    pairing = Pairing(code=new_code(), token_hash=body.token_hash, name=body.name,
                      expires_at=now + LIFETIME)
    db.add(pairing)
    db.commit()
    return PairingCreated(code=pairing.code, expires_at=pairing.expires_at)


@router.get("/{code}", response_model=PairingStatus)
def pairing_status(code: str, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                   db: Session = Depends(get_db)):
    """The mirror asks, with its own token, whether its code was claimed"""
    pairing = db.get(Pairing, normalize(code))
    token = credentials.credentials if credentials else ""
    if pairing is None or not secrets.compare_digest(pairing.token_hash, hash_token(token)):
        raise _not_found()
    if pairing.device_id is not None:
        device = db.get(Device, pairing.device_id)
        return PairingStatus(status="paired", device=device, expires_at=pairing.expires_at)
    if pairing.expires_at < datetime.now(UTC):
        raise _not_found()
    return PairingStatus(status="waiting", expires_at=pairing.expires_at)


@router.post("/{code}/claim", response_model=PairingStatus, status_code=status.HTTP_201_CREATED)
def claim_pairing(code: str, body: PairingClaim, user: User = Depends(not_demo),
                  db: Session = Depends(get_db)):
    """You scanned a mirror's QR code: add it to your account"""
    claim_limit.hit(str(user.id))
    pairing = db.get(Pairing, normalize(code), with_for_update=True)
    if pairing is None or pairing.device_id is not None or pairing.expires_at < datetime.now(UTC):
        raise _not_found()
    name = (body.name or pairing.name or "Mirror").strip()[:100] or "Mirror"
    device = Device(name=name, token_hash=pairing.token_hash, owner_id=user.id)
    db.add(device)
    db.flush()
    pairing.device_id = device.id
    db.commit()
    claim_limit.reset(str(user.id))
    return PairingStatus(status="paired", device=device, expires_at=pairing.expires_at)

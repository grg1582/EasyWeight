from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..demo import not_demo
from ..ingest import ingest
from ..models import Device, User
from ..schemas import EventBatch, EventBatchResult
from ..security import current_device, hash_token, new_token

router = APIRouter(prefix="/api/v1/events", tags=["events"])

BROWSER_NAME = "Web browser"


def _check_size(body: EventBatch) -> None:
    limit = get_settings().max_events_per_request
    if len(body.events) > limit:
        raise HTTPException(413, f"Send at most {limit} events per request")


@router.post("", response_model=EventBatchResult)
def send_events(
    body: EventBatch,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
):
    """A mirror sends what happened, in order: workout_started, set_started,
    rep, set_ended, workout_ended. Each event gets its own result, and sending
    an event again is harmless (it comes back as "duplicate")"""
    _check_size(body)
    return ingest(db, device, body.events)


def browser_device(db: Session, user: User) -> Device:
    """The user's "Web browser" device, created the first time they train in
    the dashboard. Its token is random and never used: the dashboard sends
    events with the user's own sign-in instead"""
    device = db.scalar(select(Device).where(Device.owner_id == user.id,
                                            Device.kind == "browser"))
    if device is None:
        device = Device(name=BROWSER_NAME, kind="browser", owner_id=user.id,
                        token_hash=hash_token(new_token()))
        db.add(device)
        db.flush()
    return device


@router.post("/browser", response_model=EventBatchResult)
def send_browser_events(
    body: EventBatch,
    user: User = Depends(not_demo),
    db: Session = Depends(get_db),
):
    """The same events, from a workout done with the camera in the dashboard.
    They're saved under the user's "Web browser" device"""
    _check_size(body)
    return ingest(db, browser_device(db, user), body.events)

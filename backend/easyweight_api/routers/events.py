from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..ingest import ingest
from ..models import Device
from ..schemas import EventBatch, EventBatchResult
from ..security import current_device

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", response_model=EventBatchResult)
def send_events(
    body: EventBatch,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
):
    """A mirror sends what happened, in order: workout_started, set_started,
    rep, set_ended, workout_ended. Each event gets its own result, and sending
    an event again is harmless (it comes back as "duplicate")"""
    limit = get_settings().max_events_per_request
    if len(body.events) > limit:
        raise HTTPException(413,
                            f"Send at most {limit} events per request")
    return ingest(db, device, body.events)

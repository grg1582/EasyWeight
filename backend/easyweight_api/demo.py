"""The demo account behind the "Try the demo" button.

It belongs to a made-up user with one mirror and about two months of
simulated workouts. Each time someone opens the demo, workouts are added up to
today, so its charts never go stale. The account is read-only: the API refuses
to add or remove its mirrors, and its password is random and never shown.

    python -m easyweight_api.demo        fill (or refresh) the demo account now
"""
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from pydantic import TypeAdapter
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from . import simulator
from .config import get_settings
from .ingest import ingest
from .models import Device, Event, User, Workout
from .schemas import DeviceEvent
from .security import hash_token, new_token
from .user_auth import current_user, hash_password

HISTORY_DAYS = 60
DEMO_LOCK = 0x45570001  # any number no other code locks on
KEEP_DAYS = 90
_events = TypeAdapter(list[DeviceEvent])


def is_demo(user: User) -> bool:
    return user.email == get_settings().demo_email


def not_demo(user: User = Depends(current_user)) -> User:
    """FastAPI dependency for changes the demo account may not make"""
    if is_demo(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "The demo is read-only. Create an account to add mirrors")
    return user


def demo_user(db: Session, now: datetime | None = None) -> User:
    """The demo user, created if needed, with workouts up to `now`"""
    now = now or datetime.now(UTC)
    email = get_settings().demo_email
    # Two visitors can open the demo at the same moment (say, the first two
    # after a deploy). Take turns: without this lock both would create the demo
    # user and one would fail. The lock is held until the commit below, and
    # the second visitor then finds the user the first one made
    db.execute(text("select pg_advisory_xact_lock(:key)"), {"key": DEMO_LOCK})
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(secrets.token_urlsafe(32)))
        db.add(user)
        db.flush()
    device = db.scalar(select(Device).where(Device.owner_id == user.id))
    if device is None:
        device = Device(name="Demo mirror", owner_id=user.id, token_hash=hash_token(new_token()))
        db.add(device)
        db.flush()
    top_up(db, device, now)
    db.commit()
    return user


def top_up(db: Session, device: Device, now: datetime) -> int:
    """Simulate the workouts since the device's last one, and forget the
    oldest. Returns how many events were added"""
    cutoff = now - timedelta(days=KEEP_DAYS)
    db.execute(delete(Workout).where(Workout.device_id == device.id,
                                     Workout.started_at < cutoff))
    db.execute(delete(Event).where(Event.device_id == device.id, Event.occurred_at < cutoff))
    latest = db.scalar(select(func.max(Workout.started_at))
                       .where(Workout.device_id == device.id))
    if latest is None:
        first = now - timedelta(days=HISTORY_DAYS)
    else:  # from the day after the last workout
        first = (latest + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    # Only workouts that are over by now
    events = simulator.history(first, now - timedelta(hours=1))
    batch = get_settings().max_events_per_request
    for i in range(0, len(events), batch):
        ingest(db, device, _events.validate_python(events[i:i + batch]), commit=False)
    return len(events)


if __name__ == "__main__":
    from .db import SessionLocal

    if not get_settings().demo_enabled:
        raise SystemExit("The demo is turned off (DEMO_ENABLED=false)")

    with SessionLocal() as session:
        user = demo_user(session)
        workouts = session.scalar(select(func.count()).select_from(Workout).join(Device)
                                  .where(Device.owner_id == user.id))
        print(f"Demo account {user.email}: {workouts} workouts")

"""Applies the events a device sends to the workout tables.

Each event gets its own result: a duplicate is skipped, a bad one is
rejected with a reason, and neither stops the rest of the batch. That matters
for a device sending a backlog after being offline: one bad event mustn't
block everything behind it forever.
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Device, Event, Rep, Workout, WorkoutSet
from .schemas import (
    EventBatchResult,
    EventResult,
    RepCounted,
    SetEnded,
    SetStarted,
    WorkoutEnded,
    WorkoutStarted,
)


class Rejected(Exception):
    pass


def _store(db: Session, device: Device, event) -> None:
    db.add(Event(id=event.id, device_id=device.id, type=event.type,
                 occurred_at=event.at, data=event.data.model_dump(mode="json")))
    _apply(db, device, event)


def _one(db: Session, device: Device, event) -> EventResult:
    try:
        with db.begin_nested():  # a savepoint: undo just this event if it fails
            _store(db, device, event)
            db.flush()
        return EventResult(id=event.id, status="applied")
    except IntegrityError as e:
        return EventResult(id=event.id, status="rejected",
                           reason=f"conflicts with stored data: {e.orig}")
    except Rejected as e:
        return EventResult(id=event.id, status="rejected", reason=str(e))


def ingest(db: Session, device: Device, events, commit: bool = True) -> EventBatchResult:
    """Store the events and apply them. With commit=False the caller commits
    (the demo fills its account in one transaction)"""
    ids = [event.id for event in events]
    stored = set(db.scalars(select(Event.id).where(Event.id.in_(ids)))) if ids else set()
    fresh, seen = [], set(stored)
    for event in events:
        if event.id not in seen:
            seen.add(event.id)
            fresh.append(event)
    outcome: dict = {}  # event id -> its EventResult, for the fresh ones

    # Usually every event is fine: apply them all at once, which is much faster
    # for a long backlog. If one fails, undo that and go one event at a time
    try:
        with db.begin_nested():
            for event in fresh:
                _store(db, device, event)
            db.flush()
        for event in fresh:
            outcome[event.id] = EventResult(id=event.id, status="applied")
    except (IntegrityError, Rejected):
        for event in fresh:
            outcome[event.id] = _one(db, device, event)

    # One result per event sent, in the order sent. Sent before (say, after a
    # lost connection), or twice in this batch: "duplicate"
    results = [outcome.pop(event.id, None) or EventResult(id=event.id, status="duplicate")
               for event in events]

    # When the mirror last got in touch (not when its events happened: an
    # offline backlog can be days old)
    device.last_seen_at = datetime.now(UTC)
    if commit:
        db.commit()
    else:
        db.flush()
    count = lambda s: sum(r.status == s for r in results)  # noqa: E731
    return EventBatchResult(applied=count("applied"), duplicates=count("duplicate"),
                            rejected=count("rejected"), results=results)


def _workout(db, device, workout_id, at, create=False):
    workout = db.get(Workout, workout_id)
    if workout is None:
        if not create:
            raise Rejected(f"unknown workout {workout_id}")
        workout = Workout(id=workout_id, device_id=device.id, started_at=at)
        db.add(workout)
    elif workout.device_id != device.id:
        raise Rejected(f"workout {workout_id} belongs to another device")
    return workout


def _set(db, device, set_id):
    workout_set = db.get(WorkoutSet, set_id)
    if workout_set is None:
        raise Rejected(f"unknown set {set_id}")
    if workout_set.workout.device_id != device.id:
        raise Rejected(f"set {set_id} belongs to another device")
    return workout_set


def _apply(db, device, event):
    data = event.data
    if isinstance(event, WorkoutStarted):
        _workout(db, device, data.workout_id, event.at, create=True)
    elif isinstance(event, SetStarted):
        # A device may skip workout_started: the first set starts the workout
        workout = _workout(db, device, data.workout_id, event.at, create=True)
        workout_set = db.get(WorkoutSet, data.set_id)
        if workout_set is None:
            db.add(WorkoutSet(id=data.set_id, workout=workout, exercise=data.exercise,
                              set_number=data.set_number, reps=0, started_at=event.at))
        elif workout_set.workout_id != workout.id:
            raise Rejected(f"set {data.set_id} belongs to another workout")
        else:  # the set turned out to be another exercise
            workout_set.exercise = data.exercise
            workout_set.set_number = data.set_number
    elif isinstance(event, RepCounted):
        workout_set = _set(db, device, data.set_id)
        db.add(Rep(set=workout_set, side=data.side, count=data.count, at=event.at, top=data.top))
        workout_set.reps = max(workout_set.reps, data.count)
    elif isinstance(event, SetEnded):
        workout_set = _set(db, device, data.set_id)
        workout_set.reps = data.reps
        workout_set.ended_at = event.at
    elif isinstance(event, WorkoutEnded):
        workout = _workout(db, device, data.workout_id, event.at)
        workout.ended_at = event.at

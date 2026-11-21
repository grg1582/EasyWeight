"""Applies the events a device sends to the workout tables.

Each event is handled on its own: a duplicate is skipped, a bad one is
rejected with a reason, and neither stops the rest of the batch. That matters
for a device sending a backlog after being offline: one bad event mustn't
block everything behind it forever.
"""
from datetime import UTC, datetime

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


def ingest(db: Session, device: Device, events) -> EventBatchResult:
    results = []
    for event in events:
        if db.get(Event, event.id) is not None:  # sent before, e.g. after a lost connection
            results.append(EventResult(id=event.id, status="duplicate"))
            continue
        try:
            with db.begin_nested():  # a savepoint: undo just this event if it fails
                db.add(Event(id=event.id, device_id=device.id, type=event.type,
                             occurred_at=event.at, data=event.data.model_dump(mode="json")))
                _apply(db, device, event)
                db.flush()
            results.append(EventResult(id=event.id, status="applied"))
        except IntegrityError as e:
            results.append(EventResult(id=event.id, status="rejected",
                                       reason=f"conflicts with stored data: {e.orig}"))
        except Rejected as e:
            results.append(EventResult(id=event.id, status="rejected", reason=str(e)))
    # When the mirror last got in touch (not when its events happened: an
    # offline backlog can be days old)
    device.last_seen_at = datetime.now(UTC)
    db.commit()
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

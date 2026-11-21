import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Workout, WorkoutSet
from ..schemas import DayStats, ExerciseStats, Stats

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("", response_model=Stats)
def stats(
    device_id: uuid.UUID | None = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Totals for the last `days` days: sets and reps per exercise, and reps per
    day (UTC dates). Computed by the database, not in Python"""
    since = datetime.now(UTC) - timedelta(days=days)
    sets = (
        select(WorkoutSet)
        .join(Workout)
        .where(WorkoutSet.started_at >= since)
    )
    if device_id:
        sets = sets.where(Workout.device_id == device_id)
    sets = sets.subquery()

    per_exercise = db.execute(
        select(sets.c.exercise, func.count(), func.coalesce(func.sum(sets.c.reps), 0))
        .group_by(sets.c.exercise)
        .order_by(sets.c.exercise)
    ).all()
    day = cast(func.timezone("UTC", sets.c.started_at), Date)
    per_day = db.execute(
        select(day, func.sum(sets.c.reps)).group_by(day).order_by(day)
    ).all()
    workouts = db.scalar(select(func.count(func.distinct(sets.c.workout_id))))
    return Stats(
        days=days,
        workouts=workouts,
        per_exercise=[ExerciseStats(exercise=e, sets=n, reps=r) for e, n, r in per_exercise],
        per_day=[DayStats(date=d, reps=r) for d, r in per_day],
    )

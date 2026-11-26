import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Workout, WorkoutSet
from ..schemas import DayStats, ExerciseStats, Stats
from ..user_auth import current_user
from .workouts import only_mine

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("", response_model=Stats)
def stats(
    device_id: uuid.UUID | None = None,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """The signed-in user's totals for the last `days` days: sets and reps per
    exercise, and reps per day (UTC dates). Computed by the database, not in Python"""
    since = datetime.now(UTC) - timedelta(days=days)
    sets = (
        only_mine(select(WorkoutSet).join(Workout), user, device_id)
        .where(WorkoutSet.started_at >= since)
        .subquery()
    )

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

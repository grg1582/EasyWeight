import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..auth import current_user
from ..db import get_db
from ..models import Device, User, Workout
from ..schemas import SetOut, WorkoutDetail, WorkoutPage, WorkoutSummary

router = APIRouter(prefix="/api/v1/workouts", tags=["workouts"])


def _summary(workout: Workout) -> dict:
    exercises = []
    for s in workout.sets:
        if s.exercise not in exercises:
            exercises.append(s.exercise)
    return dict(
        id=workout.id,
        device_id=workout.device_id,
        started_at=workout.started_at,
        ended_at=workout.ended_at,
        total_sets=len(workout.sets),
        total_reps=sum(s.reps for s in workout.sets),
        exercises=exercises,
    )


@router.get("", response_model=WorkoutPage)
def list_workouts(
    device_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """The signed-in user's workouts, from all their mirrors or one, newest first"""
    query = select(Workout).join(Device).where(Device.owner_id == user.id)
    if device_id:
        query = query.where(Workout.device_id == device_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    workouts = db.scalars(
        query.options(selectinload(Workout.sets))
        .order_by(Workout.started_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return WorkoutPage(items=[WorkoutSummary(**_summary(w)) for w in workouts], total=total)


@router.get("/{workout_id}", response_model=WorkoutDetail)
def get_workout(workout_id: uuid.UUID, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    """One workout with its sets. Someone else's workout is "not found", so
    ids can't be probed"""
    workout = db.scalar(
        select(Workout)
        .join(Device)
        .where(Workout.id == workout_id, Device.owner_id == user.id)
        .options(selectinload(Workout.sets))
    )
    if workout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workout not found")
    return WorkoutDetail(**_summary(workout),
                         sets=[SetOut.model_validate(s) for s in workout.sets])

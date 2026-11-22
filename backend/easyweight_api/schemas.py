"""Request and response shapes. FastAPI checks every request against these and
shows them in the interactive docs at /docs."""
import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field

from .models import Exercise, Side

# Users and sign-in


class UserCreate(BaseModel):
    email: EmailStr = Field(examples=["roy@example.com"])
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime
    is_demo: bool = Field(False, description="The read-only demo account")


class TokenPair(BaseModel):
    access_token: str = Field(description="Send as \"Authorization: Bearer <token>\". "
                                          "Lasts 15 minutes")
    refresh_token: str = Field(description="Swap it for a new pair at /api/v1/auth/refresh. "
                                           "Works once, lasts 30 days")
    token_type: Literal["bearer"] = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# Devices


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Gym mirror 1"])


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: Literal["mirror", "browser"]
    created_at: datetime
    last_seen_at: datetime | None


class DeviceCreated(DeviceOut):
    token: str = Field(description="Shown only once. The device sends it as a Bearer token")


# Events a device sends. Every event has an id chosen by the device (so sending
# it twice is harmless), the time it happened, and data depending on its type


class _Event(BaseModel):
    id: uuid.UUID
    at: AwareDatetime


class WorkoutStartedData(BaseModel):
    workout_id: uuid.UUID


class SetStartedData(BaseModel):
    workout_id: uuid.UUID
    set_id: uuid.UUID
    exercise: Exercise
    set_number: int = Field(ge=1)


class RepData(BaseModel):
    set_id: uuid.UUID
    side: Side
    count: int = Field(ge=1, description="This arm's rep count in the set, after this rep")
    top: float | None = Field(default=None, description="Top angle (or height) of the rep")


class SetEndedData(BaseModel):
    set_id: uuid.UUID
    reps: int = Field(ge=0)


class WorkoutEndedData(BaseModel):
    workout_id: uuid.UUID


class WorkoutStarted(_Event):
    type: Literal["workout_started"]
    data: WorkoutStartedData


class SetStarted(_Event):
    """Sending it again for the same set_id changes the set's exercise: a 1 rep
    set can turn out to be another exercise"""

    type: Literal["set_started"]
    data: SetStartedData


class RepCounted(_Event):
    type: Literal["rep"]
    data: RepData


class SetEnded(_Event):
    type: Literal["set_ended"]
    data: SetEndedData


class WorkoutEnded(_Event):
    type: Literal["workout_ended"]
    data: WorkoutEndedData


DeviceEvent = Annotated[
    WorkoutStarted | SetStarted | RepCounted | SetEnded | WorkoutEnded,
    Field(discriminator="type"),
]


class EventBatch(BaseModel):
    events: list[DeviceEvent] = Field(min_length=1)


class EventResult(BaseModel):
    id: uuid.UUID
    status: Literal["applied", "duplicate", "rejected"]
    reason: str | None = None


class EventBatchResult(BaseModel):
    applied: int
    duplicates: int
    rejected: int
    results: list[EventResult]


# Workouts


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise: Exercise
    set_number: int
    reps: int
    started_at: datetime
    ended_at: datetime | None


class WorkoutSummary(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    total_sets: int
    total_reps: int
    exercises: list[Exercise]


class WorkoutDetail(WorkoutSummary):
    sets: list[SetOut]


class WorkoutPage(BaseModel):
    items: list[WorkoutSummary]
    total: int


# Stats


class ExerciseStats(BaseModel):
    exercise: Exercise
    sets: int
    reps: int


class DayStats(BaseModel):
    date: date
    reps: int


class Stats(BaseModel):
    days: int
    workouts: int
    per_exercise: list[ExerciseStats]
    per_day: list[DayStats]

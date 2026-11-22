"""The database tables.

A user owns devices (mirrors). A device sends events. Each event is stored as
it arrived (events) and applied to the workout tables:

    users ─< devices ─< workouts ─< sets ─< reps
      │         ├─< events
      │         └─< pairings (a QR code that connected it)
      └─< refresh_tokens
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Exercise(enum.StrEnum):
    curl = "curl"
    raise_ = "raise"
    press = "press"


class Side(enum.StrEnum):
    left = "left"
    right = "right"


def _enum(cls, name):
    # Store the values ("raise"), not the Python names ("raise_")
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lowercase
    password_hash: Mapped[str] = mapped_column(String(200))  # Argon2, never the password
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    devices: Mapped[list["Device"]] = relationship(back_populates="owner")


class RefreshToken(Base):
    """One per sign-in. Each use replaces it with a new one, so a stolen token
    that is used after its owner already used it gives itself away"""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (Index("uq_devices_one_browser_per_owner", "owner_id", unique=True,
                            postgresql_where=text("kind = 'browser'")),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Empty for mirrors registered before user accounts existed
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    # "mirror", or "browser" for workouts done with the camera on the dashboard
    kind: Mapped[str] = mapped_column(String(20), default="mirror", server_default="mirror")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User | None] = relationship(back_populates="devices")
    workouts: Mapped[list["Workout"]] = relationship(back_populates="device")


class Workout(Base):
    """Everything one person did at the mirror, from the first rep until the
    mirror reset (they walked away, or rested too long)"""

    __tablename__ = "workouts"
    __table_args__ = (Index("ix_workouts_device_started", "device_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # chosen by the device
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device] = relationship(back_populates="workouts")
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout", order_by="WorkoutSet.started_at", cascade="all, delete-orphan"
    )


class WorkoutSet(Base):
    __tablename__ = "sets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # chosen by the device
    workout_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), index=True
    )
    exercise: Mapped[Exercise] = mapped_column(_enum(Exercise, "exercise"))
    set_number: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workout: Mapped[Workout] = relationship(back_populates="sets")
    rep_list: Mapped[list["Rep"]] = relationship(
        back_populates="set", order_by="Rep.at", cascade="all, delete-orphan"
    )


class Rep(Base):
    """One rep of one arm, kept for tempo and form analysis later"""

    __tablename__ = "reps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sets.id", ondelete="CASCADE"), index=True)
    side: Mapped[Side] = mapped_column(_enum(Side, "arm_side"))
    count: Mapped[int] = mapped_column(Integer)  # this arm's rep count in the set
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    top: Mapped[float | None] = mapped_column(Float)  # top angle or height of the rep

    set: Mapped[WorkoutSet] = relationship(back_populates="rep_list")


class Event(Base):
    """Every event exactly as a device sent it. Its id is chosen by the device,
    so an event sent twice (after a lost connection) is only applied once"""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    data: Mapped[dict] = mapped_column(JSONB)


class Pairing(Base):
    """A mirror asking to be connected by QR code. It made its own token and
    sent only the hash. Claiming the code creates the device with that hash,
    so the token itself never leaves the mirror"""

    __tablename__ = "pairings"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str | None] = mapped_column(String(100))  # suggested by the mirror
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE")
    )

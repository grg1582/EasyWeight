"""The migrations must match models.py and be reversible"""
import uuid
from datetime import UTC, datetime

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text

from conftest import alembic_config
from easyweight_api.db import Base


def test_migrations_match_the_models(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_downgrade_and_upgrade_again(engine):
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), "head")


def test_going_back_before_squats_drops_them(engine):
    """PostgreSQL can't remove enum values: the downgrade deletes what uses them
    and builds the old types again"""
    device, workout = uuid.uuid4(), uuid.uuid4()
    curl, squat = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(text("insert into devices (id, name, token_hash) values (:id, 'm', :h)"),
                     {"id": device, "h": uuid.uuid4().hex})
        conn.execute(text("insert into workouts (id, device_id, started_at) values (:id, :d, :t)"),
                     {"id": workout, "d": device, "t": now})
        for set_id, exercise, side in ((curl, "curl", "left"), (squat, "squat", "both")):
            conn.execute(text("insert into sets (id, workout_id, exercise, set_number, reps, "
                              "started_at) values (:id, :w, :e, 1, 1, :t)"),
                         {"id": set_id, "w": workout, "e": exercise, "t": now})
            conn.execute(text("insert into reps (set_id, side, count, at) "
                              "values (:s, :side, 1, :t)"),
                         {"s": set_id, "side": side, "t": now})
    try:
        command.downgrade(alembic_config(), "0004")
        with engine.connect() as conn:
            assert conn.scalars(text("select exercise::text from sets")).all() == ["curl"]
            assert conn.scalars(text("select side::text from reps")).all() == ["left"]
        command.upgrade(alembic_config(), "head")
    finally:
        with engine.begin() as conn:
            conn.execute(text("delete from devices where id = :id"), {"id": device})

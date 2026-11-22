"""The tests run against a real PostgreSQL database, given by TEST_DATABASE_URL.
Start one with Docker from the repository root:

    docker compose up -d db
    set TEST_DATABASE_URL=postgresql+psycopg://easyweight:easyweight@localhost:5432/easyweight_test

The migrations build the tables once per test run, and each test runs inside
a transaction that is rolled back afterwards, so tests don't see each other's
data.
"""
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from easyweight_api.db import get_db
from easyweight_api.main import create_app

URL = os.environ.get("TEST_DATABASE_URL")
BACKEND = Path(__file__).resolve().parent.parent

if not URL:
    pytest.exit("Set TEST_DATABASE_URL to a PostgreSQL database for the tests "
                "(see tests/conftest.py)", returncode=4)


def alembic_config():
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.attributes["database_url"] = URL
    return config


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(URL)
    with engine.begin() as conn:  # start from an empty database
        conn.execute(text("drop schema public cascade; create schema public"))
    command.upgrade(alembic_config(), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    """A session whose commits only go as far as an outer transaction that is
    rolled back when the test ends"""
    with engine.connect() as conn:
        outer = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint",
                          expire_on_commit=False)
        yield session
        session.close()
        outer.rollback()


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    """Each test starts with no sign-in attempts counted"""
    from easyweight_api.routers import auth, pairing

    auth.login_limit.clear()
    auth.signup_limit.clear()
    pairing.create_limit.clear()
    pairing.claim_limit.clear()


@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client


PASSWORD = "correct horse battery"


def sign_up(client, email="roy@example.com", password=PASSWORD):
    """Create an account: {"email", "password", "access_token", "refresh_token", "headers"}"""
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    tokens = r.json()
    return {"email": email, "password": password, **tokens,
            "headers": {"Authorization": f"Bearer {tokens['access_token']}"}}


@pytest.fixture
def user(client):
    """A signed-up user. From here on the client sends their access token,
    unless a request gives other headers (like a device's token)"""
    user = sign_up(client)
    client.headers.update(user["headers"])
    return user


@pytest.fixture
def device(client, user):
    """A device registered by `user`: {"id", "token", "headers"}"""
    r = client.post("/api/v1/devices", json={"name": "Test mirror"})
    assert r.status_code == 201, r.text
    body = r.json()
    return {"id": body["id"], "token": body["token"],
            "headers": {"Authorization": f"Bearer {body['token']}"}}


T0 = datetime(2026, 11, 1, 18, 0, tzinfo=UTC)


class Mirror:
    """Builds the events a mirror would send, like the device will in phase 3"""

    def __init__(self, start=T0):
        self.t = start
        self.workout_id = None
        self.set_id = None

    def _event(self, type_, **data):
        return {"id": str(uuid.uuid4()), "type": type_, "at": self.t.isoformat(), "data": data}

    def wait(self, seconds):
        self.t += timedelta(seconds=seconds)
        return self

    def start_workout(self):
        self.workout_id = str(uuid.uuid4())
        return self._event("workout_started", workout_id=self.workout_id)

    def start_set(self, exercise, number=1, set_id=None):
        self.set_id = set_id or str(uuid.uuid4())
        return self._event("set_started", workout_id=self.workout_id, set_id=self.set_id,
                           exercise=exercise, set_number=number)

    def rep(self, count, side="left", top=40.0):
        self.t += timedelta(seconds=2)
        return self._event("rep", set_id=self.set_id, side=side, count=count, top=top)

    def end_set(self, reps):
        return self._event("set_ended", set_id=self.set_id, reps=reps)

    def end_workout(self):
        return self._event("workout_ended", workout_id=self.workout_id)

    def full_set(self, exercise, reps, number=1):
        events = [self.start_set(exercise, number)]
        events += [self.rep(i) for i in range(1, reps + 1)]
        events.append(self.end_set(reps))
        self.wait(60)
        return events


@pytest.fixture
def mirror():
    return Mirror()


@pytest.fixture
def send(client, device):
    def send(events, headers=None):
        r = client.post("/api/v1/events", json={"events": events},
                        headers=headers or device["headers"])
        assert r.status_code == 200, r.text
        return r.json()
    return send

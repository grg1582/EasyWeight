from datetime import UTC, datetime, timedelta

import pytest

from conftest import PASSWORD, sign_up
from easyweight_api import demo, simulator
from easyweight_api.models import Device, User, Workout
from easyweight_api.ratelimit import RateLimiter


def test_simulated_workouts_look_like_a_mirror_sent_them():
    first = datetime(2026, 10, 1, tzinfo=UTC)
    events = simulator.history(first, first + timedelta(days=28), seed=1)
    types = [e["type"] for e in events]
    assert types.count("workout_started") == types.count("workout_ended")
    assert 10 <= types.count("workout_started") <= 22  # about 4 a week
    times = [e["at"] for e in events]
    assert times == sorted(times)


def test_demo_sign_in(client):
    r = client.post("/api/v1/auth/demo")
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = client.get("/api/v1/users/me", headers=headers).json()
    assert me["is_demo"] is True
    stats = client.get("/api/v1/stats?days=30", headers=headers).json()
    assert stats["workouts"] >= 8
    assert {e["exercise"] for e in stats["per_exercise"]} == {"curl", "raise", "press"}


def test_demo_is_read_only(client):
    token = client.post("/api/v1/auth/demo").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/devices", json={"name": "Mine now"}, headers=headers)
    assert r.status_code == 403
    mirror = client.get("/api/v1/devices", headers=headers).json()[0]
    assert client.delete(f"/api/v1/devices/{mirror['id']}", headers=headers).status_code == 403


def test_demo_keeps_up_to_date(db):
    now = datetime.now(UTC)
    user = demo.demo_user(db, now - timedelta(days=20))
    device = db.query(Device).filter_by(owner_id=user.id).one()
    last = db.query(Workout).filter_by(device_id=device.id).order_by(Workout.started_at).all()
    assert last[-1].started_at < now - timedelta(days=19)

    demo.demo_user(db, now)  # three weeks later: workouts added up to now
    latest = max(w.started_at for w in db.query(Workout).filter_by(device_id=device.id))
    assert latest > now - timedelta(days=4)
    assert db.query(User).filter_by(email=user.email).count() == 1


def test_demo_can_be_turned_off(client, monkeypatch):
    from easyweight_api.config import get_settings

    monkeypatch.setattr(get_settings(), "demo_enabled", False)
    assert client.post("/api/v1/auth/demo").status_code == 404


def test_too_many_wrong_passwords(client):
    sign_up(client)
    for _ in range(10):
        r = client.post("/api/v1/auth/login",
                        data={"username": "roy@example.com", "password": "wrong guess"})
        assert r.status_code == 401
    r = client.post("/api/v1/auth/login",
                    data={"username": "roy@example.com", "password": PASSWORD})
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0


def test_too_many_signups_from_one_address(client):
    for i in range(10):
        sign_up(client, f"user{i}@example.com")
    r = client.post("/api/v1/auth/register",
                    json={"email": "one-more@example.com", "password": PASSWORD})
    assert r.status_code == 429


def test_rate_limiter_window():
    now = [0.0]
    limiter = RateLimiter(2, 60, clock=lambda: now[0])
    limiter.hit("a")
    limiter.hit("a")
    with pytest.raises(Exception, match="Too many"):
        limiter.hit("a")
    limiter.hit("b")  # others aren't affected
    now[0] = 61
    limiter.hit("a")  # the window moved on


def test_production_needs_a_real_secret(monkeypatch):
    from pydantic import ValidationError

    from easyweight_api.config import Settings

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production")
    assert Settings(environment="production", jwt_secret="x" * 40).jwt_secret == "x" * 40


def test_database_urls_from_hosts_work():
    from easyweight_api.config import Settings

    url = Settings(database_url="postgres://u:p@host.neon.tech/db?sslmode=require").database_url
    assert url == "postgresql+psycopg://u:p@host.neon.tech/db?sslmode=require"

from datetime import UTC, datetime, timedelta

from conftest import Mirror


def make_workout(send, start, sets):
    m = Mirror(start)
    events = [m.start_workout()]
    for exercise, reps, number in sets:
        events += m.full_set(exercise, reps, number)
    events.append(m.end_workout())
    send(events)
    return m.workout_id


def test_list_newest_first_with_paging(client, send):
    t = datetime.now(UTC) - timedelta(days=3)
    ids = [make_workout(send, t + timedelta(days=i), [("curl", 5, 1)]) for i in range(3)]
    page = client.get("/api/v1/workouts?limit=2").json()
    assert page["total"] == 3
    assert [w["id"] for w in page["items"]] == [ids[2], ids[1]]
    page2 = client.get("/api/v1/workouts?limit=2&offset=2").json()
    assert [w["id"] for w in page2["items"]] == [ids[0]]


def test_summary(client, send):
    make_workout(send, datetime.now(UTC), [("curl", 10, 1), ("press", 6, 1), ("curl", 8, 2)])
    w = client.get("/api/v1/workouts").json()["items"][0]
    assert w["total_sets"] == 3
    assert w["total_reps"] == 24
    assert w["exercises"] == ["curl", "press"]


def test_filter_by_device(client, send, device):
    make_workout(send, datetime.now(UTC), [("curl", 5, 1)])
    other = client.post("/api/v1/devices", json={"name": "Other"}).json()
    assert client.get(f"/api/v1/workouts?device_id={device['id']}").json()["total"] == 1
    assert client.get(f"/api/v1/workouts?device_id={other['id']}").json()["total"] == 0


def test_unknown_workout(client):
    r = client.get("/api/v1/workouts/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_stats(client, send):
    today = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
    make_workout(send, today - timedelta(days=1), [("curl", 10, 1), ("curl", 8, 2)])
    make_workout(send, today, [("raise", 12, 1), ("curl", 6, 1)])
    make_workout(send, today - timedelta(days=60), [("press", 5, 1)])  # too old

    s = client.get("/api/v1/stats?days=30").json()
    assert s["workouts"] == 2
    assert {e["exercise"]: (e["sets"], e["reps"]) for e in s["per_exercise"]} == {
        "curl": (3, 24), "raise": (1, 12)}
    assert [d["reps"] for d in s["per_day"]] == [18, 18]
    assert s["per_day"][-1]["date"] == today.date().isoformat()


def test_stats_when_empty(client):
    s = client.get("/api/v1/stats").json()
    assert s == {"days": 30, "workouts": 0, "per_exercise": [], "per_day": []}

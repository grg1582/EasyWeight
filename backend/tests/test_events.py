from datetime import UTC, datetime, timedelta

from easyweight_api.models import Event, Rep, WorkoutSet


def test_a_whole_workout(client, send, mirror):
    events = [mirror.start_workout()]
    events += mirror.full_set("curl", 10, number=1)
    events += mirror.full_set("curl", 8, number=2)
    events.append(mirror.end_workout())
    result = send(events)
    assert result["applied"] == len(events)
    assert result["duplicates"] == result["rejected"] == 0

    workout = client.get(f"/api/v1/workouts/{mirror.workout_id}").json()
    assert [(s["exercise"], s["set_number"], s["reps"]) for s in workout["sets"]] == [
        ("curl", 1, 10), ("curl", 2, 8)]
    assert workout["total_reps"] == 18
    assert workout["ended_at"] is not None


def test_sending_again_is_harmless(send, mirror, db):
    events = [mirror.start_workout()] + mirror.full_set("raise", 5)
    send(events)
    result = send(events)  # e.g. the answer was lost and the device retried
    assert result["applied"] == 0
    assert result["duplicates"] == len(events)
    assert db.query(Rep).count() == 5
    assert db.query(Event).count() == len(events)


def test_set_started_again_changes_the_exercise(client, send, mirror):
    """The mirror decided a 1 rep "curl" was really the start of a press set"""
    send([mirror.start_workout(), mirror.start_set("curl"), mirror.rep(1)])
    set_id = mirror.set_id
    send([mirror.start_set("press", set_id=set_id), mirror.rep(2), mirror.end_set(2)])
    sets = client.get(f"/api/v1/workouts/{mirror.workout_id}").json()["sets"]
    assert [(s["exercise"], s["reps"]) for s in sets] == [("press", 2)]


def test_first_set_starts_the_workout(client, send, mirror):
    mirror.start_workout()  # made the workout id, but the event is never sent
    send(mirror.full_set("curl", 3))
    assert client.get(f"/api/v1/workouts/{mirror.workout_id}").status_code == 200


def test_bad_event_does_not_block_the_rest(send, mirror, db):
    orphan = mirror.start_workout()
    bad_rep = mirror._event("rep", set_id="00000000-0000-0000-0000-000000000000",
                            side="left", count=1)
    result = send([orphan, bad_rep, *mirror.full_set("curl", 2)])
    statuses = [r["status"] for r in result["results"]]
    assert statuses[1] == "rejected"
    assert "unknown set" in result["results"][1]["reason"]
    assert statuses.count("applied") == len(statuses) - 1
    assert db.query(WorkoutSet).count() == 1


def test_device_cannot_touch_another_devices_workout(client, send, mirror):
    send([mirror.start_workout(), mirror.start_set("curl")])
    other = client.post("/api/v1/devices", json={"name": "Other"}).json()
    headers = {"Authorization": f"Bearer {other['token']}"}
    result = send([mirror.rep(1), mirror.end_workout()], headers=headers)
    assert result["rejected"] == 2
    assert "another device" in result["results"][0]["reason"]


def test_events_need_a_device_token(client, mirror):
    r = client.post("/api/v1/events", json={"events": [mirror.start_workout()]})
    assert r.status_code == 401


def test_invalid_events_are_refused(client, device, mirror):
    bad = mirror.start_workout()
    bad["type"] = "dance"
    r = client.post("/api/v1/events", json={"events": [bad]}, headers=device["headers"])
    assert r.status_code == 422
    naive = mirror.start_workout()
    naive["at"] = "2026-11-01T18:00:00"  # no time zone
    r = client.post("/api/v1/events", json={"events": [naive]}, headers=device["headers"])
    assert r.status_code == 422


def test_device_last_seen_is_when_it_sent(client, send, mirror, device):
    before = datetime.now(UTC)
    send([mirror.start_workout()])  # an event from weeks ago, sent now
    me = client.get("/api/v1/devices/me", headers=device["headers"]).json()
    assert datetime.fromisoformat(me["last_seen_at"]) >= before - timedelta(seconds=1)


def test_the_same_event_twice_in_one_batch(send, mirror, db):
    start = mirror.start_workout()
    result = send([start, start])
    assert [r["status"] for r in result["results"]] == ["applied", "duplicate"]
    assert db.query(Event).count() == 1


def test_a_long_backlog_in_one_batch(client, send, mirror):
    events = [mirror.start_workout()]
    for number in range(1, 6):
        events += mirror.full_set("curl", 12, number)
    events.append(mirror.end_workout())
    assert send(events)["applied"] == len(events)
    workout = client.get(f"/api/v1/workouts/{mirror.workout_id}").json()
    assert [s["reps"] for s in workout["sets"]] == [12] * 5


def test_a_workout_from_the_browser(client, user, mirror):
    """Training with the camera on the dashboard: the user's own sign-in sends
    the events, and they're saved under a "Web browser" device"""
    events = [mirror.start_workout(), *mirror.full_set("curl", 6), mirror.end_workout()]
    result = client.post("/api/v1/events/browser", json={"events": events}).json()
    assert result["applied"] == len(events)

    devices = client.get("/api/v1/devices").json()
    assert [(d["name"], d["kind"]) for d in devices] == [("Web browser", "browser")]
    workout = client.get(f"/api/v1/workouts/{mirror.workout_id}").json()
    assert workout["total_reps"] == 6
    assert workout["device_id"] == devices[0]["id"]


def test_the_browser_device_is_made_once(client, user, mirror):
    client.post("/api/v1/events/browser", json={"events": [mirror.start_workout()]})
    client.post("/api/v1/events/browser", json={"events": [mirror.start_workout()]})
    assert len(client.get("/api/v1/devices").json()) == 1
    assert len(client.get("/api/v1/workouts").json()["items"]) == 2


def test_browser_events_need_a_signed_in_user(client, mirror):
    r = client.post("/api/v1/events/browser", json={"events": [mirror.start_workout()]})
    assert r.status_code == 401


def test_the_demo_cannot_save_browser_workouts(client, mirror):
    token = client.post("/api/v1/auth/demo").json()["access_token"]
    r = client.post("/api/v1/events/browser", json={"events": [mirror.start_workout()]},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_mirrors_are_mirrors(client, device):
    assert client.get("/api/v1/devices/me", headers=device["headers"]).json()["kind"] == "mirror"

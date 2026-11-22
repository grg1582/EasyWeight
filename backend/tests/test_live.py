"""The live WebSocket: a dashboard hears about new events as they arrive"""
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

from conftest import sign_up
from easyweight_api.config import get_settings
from easyweight_api.live import hub


def connect(client, token):
    ws = client.websocket_connect("/api/v1/live")
    socket = ws.__enter__()
    socket.send_json({"token": token})
    return ws, socket


def test_a_dashboard_hears_new_events(client, user, device, mirror, send):
    ws, socket = connect(client, user["access_token"])
    try:
        assert socket.receive_json() == {"type": "ready"}
        events = [mirror.start_workout(), *mirror.full_set("curl", 2)]
        send(events)
        message = socket.receive_json()
        assert message["type"] == "events"
        assert message["device"] == {"id": device["id"], "name": "Test mirror", "kind": "mirror"}
        assert [e["type"] for e in message["events"]] == [
            "workout_started", "set_started", "rep", "rep", "set_ended"]
        assert message["events"][2]["data"]["count"] == 1
    finally:
        ws.__exit__(None, None, None)


def test_only_new_events_are_sent(client, user, device, mirror, send):
    events = [mirror.start_workout(), mirror.start_set("curl")]
    send(events)
    ws, socket = connect(client, user["access_token"])
    try:
        socket.receive_json()  # ready
        rep = mirror.rep(1)
        send([*events, rep])  # the first two again: duplicates
        message = socket.receive_json()
        assert [e["id"] for e in message["events"]] == [rep["id"]]
    finally:
        ws.__exit__(None, None, None)


def test_workouts_from_the_browser_are_sent_too(client, user, mirror):
    ws, socket = connect(client, user["access_token"])
    try:
        socket.receive_json()
        r = client.post("/api/v1/events/browser", json={"events": [mirror.start_workout()]})
        assert r.status_code == 200
        message = socket.receive_json()
        assert message["device"]["kind"] == "browser"
    finally:
        ws.__exit__(None, None, None)


def test_nobody_hears_someone_elses_events(client, user, device, mirror, send):
    other = sign_up(client, email="other@example.com")
    ws, socket = connect(client, other["access_token"])
    try:
        socket.receive_json()
        send([mirror.start_workout()])
        send_mine = client.post("/api/v1/events/browser", json={"events": [mirror.start_workout()]},
                                headers=other["headers"])
        assert send_mine.status_code == 200
        # The first thing the other user hears is their own workout, not Roy's
        assert socket.receive_json()["device"]["kind"] == "browser"
    finally:
        ws.__exit__(None, None, None)


@pytest.mark.parametrize("first", [{"token": "nonsense"}, {"nothing": 1}, {"token": None}])
def test_a_bad_token_is_turned_away(client, first):
    with client.websocket_connect("/api/v1/live") as socket:
        socket.send_json(first)
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4401


def test_a_refresh_token_is_turned_away(client, user):
    with client.websocket_connect("/api/v1/live") as socket:
        socket.send_json({"token": user["refresh_token"]})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4401


def test_the_socket_closes_when_the_token_expires(client, user):
    claims = jwt.decode(user["access_token"], options={"verify_signature": False})
    now = datetime.now(UTC)
    short = jwt.encode({**claims, "iat": now, "exp": now + timedelta(seconds=1)},
                       get_settings().jwt_secret, algorithm="HS256")
    with client.websocket_connect("/api/v1/live") as socket:
        socket.send_json({"token": short})
        assert socket.receive_json() == {"type": "ready"}
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4401


def test_closing_the_dashboard_stops_listening(client, user):
    claims = jwt.decode(user["access_token"], options={"verify_signature": False})
    user_id = uuid.UUID(claims["sub"])
    with client.websocket_connect("/api/v1/live") as socket:
        socket.send_json({"token": user["access_token"]})
        socket.receive_json()
        assert hub.listeners(user_id) == 1
    # The server notices the close a moment later
    for _ in range(50):
        if hub.listeners(user_id) == 0:
            break
        time.sleep(0.02)
    assert hub.listeners(user_id) == 0

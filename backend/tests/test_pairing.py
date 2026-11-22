"""Connecting a mirror by QR code: the mirror's token never leaves it"""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from conftest import sign_up
from easyweight_api.models import Pairing


def mirror_token():
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def start(client, token_hash, name="Hallway mirror"):
    r = client.post("/api/v1/pairing", json={"token_hash": token_hash, "name": name},
                    headers={"Authorization": ""})
    assert r.status_code == 201, r.text
    return r.json()["code"]


def status_of(client, code, token):
    return client.get(f"/api/v1/pairing/{code}", headers={"Authorization": f"Bearer {token}"})


def test_scan_claim_and_send(client, user, mirror):
    token, token_hash = mirror_token()
    code = start(client, token_hash)
    assert len(code) == 8 and code.isupper()
    assert status_of(client, code, token).json()["status"] == "waiting"

    # On the phone: the code from the QR code, typed any which way
    pretty = f"{code[:4].lower()}-{code[4:].lower()}"
    r = client.post(f"/api/v1/pairing/{pretty}/claim", json={})
    assert r.status_code == 201, r.text
    assert r.json()["device"]["name"] == "Hallway mirror"

    answer = status_of(client, code, token).json()
    assert answer["status"] == "paired"
    device_id = answer["device"]["id"]

    # The mirror's own token works now, and the workout lands in the account
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/devices/me", headers=headers).json()["id"] == device_id
    r = client.post("/api/v1/events", json={"events": [mirror.start_workout()]}, headers=headers)
    assert r.json()["applied"] == 1
    assert [d["id"] for d in client.get("/api/v1/devices").json()] == [device_id]


def test_the_user_can_rename_it_when_claiming(client, user):
    _, token_hash = mirror_token()
    code = start(client, token_hash)
    r = client.post(f"/api/v1/pairing/{code}/claim", json={"name": "Garage"})
    assert r.json()["device"]["name"] == "Garage"


def test_only_the_mirror_can_ask_about_its_code(client, user):
    token, token_hash = mirror_token()
    code = start(client, token_hash)
    assert status_of(client, code, "someone else's token").status_code == 404
    assert status_of(client, "ZZZZZZZZ", token).status_code == 404


def test_a_code_works_once(client, user):
    _, token_hash = mirror_token()
    code = start(client, token_hash)
    assert client.post(f"/api/v1/pairing/{code}/claim", json={}).status_code == 201
    other = sign_up(client, email="other@example.com")
    r = client.post(f"/api/v1/pairing/{code}/claim", json={}, headers=other["headers"])
    assert r.status_code == 404


def test_codes_expire(client, user, db):
    token, token_hash = mirror_token()
    code = start(client, token_hash)
    db.execute(update(Pairing).where(Pairing.code == code)
               .values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    assert client.post(f"/api/v1/pairing/{code}/claim", json={}).status_code == 404
    assert status_of(client, code, token).status_code == 404


def test_a_token_can_only_be_used_once(client, user):
    _, token_hash = mirror_token()
    start(client, token_hash)
    r = client.post("/api/v1/pairing", json={"token_hash": token_hash})
    assert r.status_code == 409


def test_the_mirror_sends_a_hash_not_a_token(client):
    r = client.post("/api/v1/pairing", json={"token_hash": "my-secret-token"})
    assert r.status_code == 422


def test_claiming_needs_a_signed_in_user_and_not_the_demo(client):
    _, token_hash = mirror_token()
    code = start(client, token_hash)
    assert client.post(f"/api/v1/pairing/{code}/claim", json={}).status_code == 401
    demo = client.post("/api/v1/auth/demo").json()
    r = client.post(f"/api/v1/pairing/{code}/claim", json={},
                    headers={"Authorization": f"Bearer {demo['access_token']}"})
    assert r.status_code == 403


def test_guessing_codes_is_rate_limited(client, user):
    for _ in range(10):
        assert client.post("/api/v1/pairing/AAAAAAAA/claim", json={}).status_code == 404
    assert client.post("/api/v1/pairing/AAAAAAAA/claim", json={}).status_code == 429

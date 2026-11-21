from conftest import sign_up


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_device_returns_token_once(client, user):
    r = client.post("/api/v1/devices", json={"name": "Gym mirror"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Gym mirror"
    assert len(body["token"]) >= 40
    listed = client.get("/api/v1/devices").json()
    assert [d["id"] for d in listed] == [body["id"]]
    assert "token" not in listed[0]


def test_registering_a_device_needs_a_signed_in_user(client):
    assert client.post("/api/v1/devices", json={"name": "Gym mirror"}).status_code == 401


def test_the_device_belongs_to_the_user(db, device):
    from easyweight_api.models import Device, User

    owner = db.get(User, db.get(Device, device["id"]).owner_id)
    assert owner.email == "roy@example.com"


def test_token_identifies_the_device(client, device):
    r = client.get("/api/v1/devices/me", headers=device["headers"])
    assert r.status_code == 200
    assert r.json()["id"] == device["id"]
    assert "token" not in r.json()


def test_token_is_not_stored_in_plain_text(db, device):
    from easyweight_api.models import Device

    stored = db.get(Device, device["id"])
    assert stored.token_hash != device["token"]


def test_missing_or_wrong_token(client):
    assert client.get("/api/v1/devices/me").status_code == 401
    r = client.get("/api/v1/devices/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_device_name_is_required(client, user):
    assert client.post("/api/v1/devices", json={"name": ""}).status_code == 422


def test_users_only_see_their_own_devices(client, device):
    other = sign_up(client, "dana@example.com")
    assert client.get("/api/v1/devices", headers=other["headers"]).json() == []


def test_remove_device(client, device, send, mirror):
    send([mirror.start_workout()])
    other = sign_up(client, "dana@example.com")
    url = f"/api/v1/devices/{device['id']}"
    assert client.delete(url, headers=other["headers"]).status_code == 404
    assert client.delete(url).status_code == 204
    assert client.get("/api/v1/devices").json() == []
    assert client.get("/api/v1/workouts").json()["total"] == 0
    assert client.get("/api/v1/devices/me", headers=device["headers"]).status_code == 401

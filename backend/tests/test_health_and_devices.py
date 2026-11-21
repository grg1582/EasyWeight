def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_device_returns_token_once(client):
    r = client.post("/api/v1/devices", json={"name": "Gym mirror"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Gym mirror"
    assert len(body["token"]) >= 40


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


def test_device_name_is_required(client):
    assert client.post("/api/v1/devices", json={"name": ""}).status_code == 422

from datetime import UTC, datetime, timedelta

import jwt

from conftest import PASSWORD, sign_up
from easyweight_api.config import get_settings


def login(client, email="roy@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


def refresh(client, token):
    return client.post("/api/v1/auth/refresh", json={"refresh_token": token})


def me(client, access_token):
    return client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})


def test_register_signs_in(client):
    user = sign_up(client)
    r = me(client, user["access_token"])
    assert r.status_code == 200
    assert r.json()["email"] == "roy@example.com"
    assert "password_hash" not in r.json()


def test_email_is_case_insensitive(client):
    sign_up(client, "Roy@Example.com")
    assert login(client, "roy@example.COM").status_code == 200
    r = client.post("/api/v1/auth/register",
                    json={"email": "ROY@example.com", "password": PASSWORD})
    assert r.status_code == 409


def test_register_checks_input(client):
    post = client.post
    assert post("/api/v1/auth/register",
                json={"email": "not-an-email", "password": PASSWORD}).status_code == 422
    assert post("/api/v1/auth/register",
                json={"email": "a@example.com", "password": "short"}).status_code == 422


def test_password_is_hashed(db, client):
    from easyweight_api.models import User

    sign_up(client)
    stored = db.query(User).one()
    assert PASSWORD not in stored.password_hash
    assert stored.password_hash.startswith("$argon2")


def test_login(client):
    sign_up(client)
    r = login(client)
    assert r.status_code == 200
    assert me(client, r.json()["access_token"]).status_code == 200


def test_wrong_password_or_unknown_email(client):
    sign_up(client)
    assert login(client, password="wrong password").status_code == 401
    r = login(client, email="nobody@example.com")
    assert r.status_code == 401
    assert r.json()["detail"] == "Wrong email or password"  # doesn't say which


def test_bad_access_tokens(client):
    user = sign_up(client)
    assert client.get("/api/v1/users/me").status_code == 401
    assert me(client, "garbage").status_code == 401
    # A refresh token is not an access token
    assert me(client, user["refresh_token"]).status_code == 401
    # Nor is a token signed with another secret
    secret = "a guessed secret, long enough for HS256"
    forged = jwt.encode({"sub": "x", "type": "access"}, secret, algorithm="HS256")
    assert me(client, forged).status_code == 401


def test_expired_access_token(client):
    user = sign_up(client)
    sub = jwt.decode(user["access_token"], options={"verify_signature": False})["sub"]
    past = datetime.now(UTC) - timedelta(minutes=1)
    expired = jwt.encode({"sub": sub, "type": "access", "exp": past},
                         get_settings().jwt_secret, algorithm="HS256")
    r = me(client, expired)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_refresh_gives_a_new_pair(client):
    user = sign_up(client)
    r = refresh(client, user["refresh_token"])
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != user["refresh_token"]
    assert me(client, new["access_token"]).status_code == 200
    assert refresh(client, new["refresh_token"]).status_code == 200


def test_refresh_token_works_once_and_reuse_signs_out_everywhere(client):
    user = sign_up(client)
    new = refresh(client, user["refresh_token"]).json()
    # Someone uses the old token again (a thief, or the owner after a thief)
    assert refresh(client, user["refresh_token"]).status_code == 401
    # So the newest one stops working too, and signing in again is needed
    assert refresh(client, new["refresh_token"]).status_code == 401
    assert refresh(client, login(client).json()["refresh_token"]).status_code == 200


def test_access_token_cant_refresh(client):
    user = sign_up(client)
    assert refresh(client, user["access_token"]).status_code == 401


def test_logout(client):
    user = sign_up(client)
    other_sign_in = login(client).json()
    r = client.post("/api/v1/auth/logout", json={"refresh_token": user["refresh_token"]})
    assert r.status_code == 204
    assert refresh(client, user["refresh_token"]).status_code == 401
    # Signing out of one browser leaves the others signed in
    assert refresh(client, other_sign_in["refresh_token"]).status_code == 200
    # Signing out twice, or with a bad token, is harmless
    for token in (user["refresh_token"], "garbage"):
        r = client.post("/api/v1/auth/logout", json={"refresh_token": token})
        assert r.status_code == 204

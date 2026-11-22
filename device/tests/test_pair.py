"""Connecting the mirror by QR code, against a fake server"""
import hashlib

import pytest

from easyweight.pair import PairingFailed, pair, pretty, qr_image


class FakeServer:
    def __init__(self, waits=2, expire=False):
        self.waits = waits
        self.expire = expire
        self.token_hash = None
        self.calls = []

    def __call__(self, method, url, body=None, token=None, **_):
        self.calls.append((method, url))
        if method == "POST":
            self.token_hash = body["token_hash"]
            return 201, {"code": "K7QM3XPA", "expires_at": "2026-11-22T18:10:00Z"}
        assert hashlib.sha256(token.encode()).hexdigest() == self.token_hash
        if self.expire:
            return 404, {"detail": "This code doesn't exist or has expired"}
        if self.waits:
            self.waits -= 1
            return 200, {"status": "waiting"}
        return 200, {"status": "paired", "device": {"id": "d1", "name": "Hallway"}}


def test_pairs_and_keeps_its_own_token():
    server = FakeServer()
    shown = []
    config = pair("https://api.example/", "https://site.example", "Hallway",
                  show=lambda link, code: shown.append((link, code)),
                  wait=lambda s: True, request=server)
    assert shown == [("https://site.example/pair/K7QM3XPA", "K7QM-3XPA")]
    assert config["device_id"] == "d1" and config["api_url"] == "https://api.example"
    # Only the hash went to the server; the token stays here
    assert hashlib.sha256(config["token"].encode()).hexdigest() == server.token_hash
    assert config["token"] not in str(server.calls)
    assert len([c for c in server.calls if c[0] == "GET"]) == 3


def test_an_expired_code_stops():
    with pytest.raises(PairingFailed, match="expired"):
        pair("https://api.example", "https://site.example", "x", lambda *a: None,
             lambda s: True, request=FakeServer(expire=True))


def test_cancelling_stops():
    with pytest.raises(PairingFailed, match="Cancelled"):
        pair("https://api.example", "https://site.example", "x", lambda *a: None,
             lambda s: False, request=FakeServer())


def test_the_code_is_easy_to_read():
    assert pretty("K7QM3XPA") == "K7QM-3XPA"


def test_the_qr_code_has_a_quiet_zone():
    image = qr_image("https://easyweight.onrender.com/pair/K7QM3XPA", 300)
    assert image.shape[0] == image.shape[1] <= 300
    assert image[0].min() == 255 and image[:, 0].min() == 255  # white border
    assert image.min() == 0

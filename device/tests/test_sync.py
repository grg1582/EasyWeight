"""The outbox and the sender, against a small fake server"""
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from easyweight.register import main as register
from easyweight.sync import Outbox, Sender, load_device_config


def event(n):
    return {"id": str(uuid.uuid4()), "type": "rep", "at": "2026-11-21T10:00:00+00:00",
            "data": {"n": n}}


class FakeServer:
    """Answers like the backend. `mode` changes how it answers"""

    def __init__(self):
        self.received = []  # every batch it got
        self.mode = "ok"
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                token = self.headers.get("Authorization")
                if self.path == "/api/v1/devices":
                    return self.answer(201, {"id": "dev-1", "name": body["name"],
                                             "token": "secret"})
                if token != "Bearer secret":
                    return self.answer(401, {"detail": "Unknown device token"})
                if fake.mode == "error":
                    return self.answer(500, {"detail": "boom"})
                if fake.mode == "invalid":
                    return self.answer(422, {"detail": "bad"})
                fake.received.append(body["events"])
                results = [{"id": e["id"], "status": "rejected" if e["data"].get("bad")
                            else "applied", "reason": None} for e in body["events"]]
                return self.answer(200, {"applied": len(results), "duplicates": 0,
                                         "rejected": 0, "results": results})

            def answer(self, status, body):
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = FakeServer()
    yield s
    s.close()


@pytest.fixture
def outbox(tmp_path):
    box = Outbox(tmp_path / "outbox.db")
    yield box
    box.close()


def test_outbox_keeps_order_and_ignores_duplicates(outbox):
    events = [event(i) for i in range(5)]
    outbox.add(events)
    outbox.add(events[:2])  # added twice
    assert [e["data"]["n"] for e in outbox.peek()] == [0, 1, 2, 3, 4]
    outbox.remove([events[0]["id"], events[2]["id"]])
    assert [e["data"]["n"] for e in outbox.peek()] == [1, 3, 4]


def test_outbox_survives_a_restart(tmp_path):
    box = Outbox(tmp_path / "outbox.db")
    box.add([event(1), event(2)])
    box.close()
    again = Outbox(tmp_path / "outbox.db")
    assert len(again) == 2
    again.close()


def test_sends_in_batches_and_empties_the_outbox(server, outbox):
    outbox.add([event(i) for i in range(250)])
    sender = Sender(outbox, server.url, "secret", batch_size=100)
    assert [sender.send_once() for _ in range(4)] == ["sent", "sent", "sent", "idle"]
    assert [len(b) for b in server.received] == [100, 100, 50]
    assert [e["data"]["n"] for b in server.received for e in b] == list(range(250))
    assert len(outbox) == 0


def test_server_down_keeps_events(outbox):
    outbox.add([event(1)])
    sender = Sender(outbox, "http://127.0.0.1:9", "secret")  # nothing listens there
    assert sender.send_once() == "offline"
    assert sender.online is False
    assert len(outbox) == 1


def test_server_error_keeps_events(server, outbox):
    server.mode = "error"
    outbox.add([event(1)])
    assert Sender(outbox, server.url, "secret").send_once() == "offline"
    assert len(outbox) == 1
    server.mode = "ok"  # the server recovers
    assert Sender(outbox, server.url, "secret").send_once() == "sent"
    assert len(outbox) == 0


def test_bad_token_keeps_events(server, outbox):
    outbox.add([event(1)])
    assert Sender(outbox, server.url, "wrong").send_once() == "refused"
    assert len(outbox) == 1


def test_rejected_event_does_not_block_the_rest(server, outbox):
    bad = event(1)
    bad["data"]["bad"] = True
    outbox.add([bad, event(2)])
    assert Sender(outbox, server.url, "secret").send_once() == "sent"
    assert len(outbox) == 0


def test_invalid_batch_is_kept_aside_not_lost(server, outbox):
    server.mode = "invalid"
    outbox.add([event(1), event(2)])
    assert Sender(outbox, server.url, "secret").send_once() == "sent"
    assert len(outbox) == 0
    assert outbox.dead_count() == 2


def test_background_thread_sends(server, outbox):
    sender = Sender(outbox, server.url, "secret", interval=0.05).start()
    outbox.add([event(1), event(2)])
    for _ in range(100):
        if not len(outbox):
            break
        threading.Event().wait(0.05)
    sender.stop()
    assert len(outbox) == 0


def test_register_saves_the_token(server, tmp_path, capsys):
    path = tmp_path / "device.json"
    register(["--api-url", server.url, "--name", "Home mirror", "--config", str(path)])
    config = load_device_config(path)
    assert config == {"api_url": server.url, "device_id": "dev-1", "name": "Home mirror",
                      "token": "secret"}
    assert "Registered" in capsys.readouterr().out

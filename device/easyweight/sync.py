"""Sends the mirror's events to the backend, and keeps them safe until it can.

Events go into an outbox (a small SQLite database on disk) the moment they
happen. A background thread sends them in order, and only deletes an event
once the server has answered for it. No network, server down, or the mirror
restarted: the events wait in the outbox and go out when the server is back.
The server ignores an event it already has, so sending one twice is harmless.
"""
import json
import logging
import sqlite3
import threading
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEVICE_CONFIG = DATA_DIR / "device.json"
OUTBOX = DATA_DIR / "outbox.db"


# Device config: which server, and this mirror's token (written by register)

def load_device_config(path=DEVICE_CONFIG):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_device_config(config, path=DEVICE_CONFIG):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def api_request(method, url, body=None, token=None, timeout=10):
    """A JSON request. Returns (status, parsed body). Raises urllib.error.URLError
    (or OSError) when the server can't be reached"""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as e:  # the server answered, with an error code
        try:
            detail = json.loads(e.read() or b"null")
        except ValueError:
            detail = None
        return e.code, detail


# Outbox

class Outbox:
    """Events waiting to be sent, in the order they happened. Safe to use from
    the main loop and the sender thread at the same time"""

    def __init__(self, path=OUTBOX):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.execute("CREATE TABLE IF NOT EXISTS outbox ("
                             "seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE, body TEXT)")
            # Events the server refused as a whole batch. Kept, never thrown away
            self._db.execute("CREATE TABLE IF NOT EXISTS dead ("
                             "id TEXT PRIMARY KEY, body TEXT, reason TEXT)")

    def add(self, events):
        if not events:
            return
        with self._lock, self._db:
            self._db.executemany("INSERT OR IGNORE INTO outbox (id, body) VALUES (?, ?)",
                                 [(e["id"], json.dumps(e)) for e in events])

    def peek(self, limit=100):
        """The oldest events, without removing them"""
        with self._lock:
            rows = self._db.execute("SELECT body FROM outbox ORDER BY seq LIMIT ?",
                                    (limit,)).fetchall()
        return [json.loads(body) for (body,) in rows]

    def remove(self, ids):
        with self._lock, self._db:
            self._db.executemany("DELETE FROM outbox WHERE id = ?", [(i,) for i in ids])

    def bury(self, events, reason):
        """Move events out of the way, keeping them for a person to look at"""
        with self._lock, self._db:
            self._db.executemany("INSERT OR REPLACE INTO dead (id, body, reason) VALUES (?, ?, ?)",
                                 [(e["id"], json.dumps(e), reason) for e in events])
            self._db.executemany("DELETE FROM outbox WHERE id = ?", [(e["id"],) for e in events])

    def __len__(self):
        with self._lock:
            return self._db.execute("SELECT count(*) FROM outbox").fetchone()[0]

    def dead_count(self):
        with self._lock:
            return self._db.execute("SELECT count(*) FROM dead").fetchone()[0]

    def close(self):
        self._db.close()


# Sender

class Sender:
    """Sends the outbox to the server in the background, in batches"""

    MAX_BACKOFF = 60  # seconds between tries while the server can't be reached

    def __init__(self, outbox, api_url, token, batch_size=100, interval=1.0):
        self.outbox = outbox
        self.url = api_url.rstrip("/") + "/api/v1/events"
        self.token = token
        self.batch_size = batch_size
        self.interval = interval
        self.online = None  # None until the first try
        self._stop = threading.Event()
        self._thread = None

    def send_once(self):
        """Send one batch. Returns "idle" (nothing to send), "sent", "offline"
        (couldn't reach the server, or it failed) or "refused" (bad token)"""
        events = self.outbox.peek(self.batch_size)
        if not events:
            return "idle"
        try:
            status, body = api_request("POST", self.url, {"events": events}, self.token)
        except (urllib.error.URLError, OSError) as e:
            self._set_online(False, e)
            return "offline"
        if status == 200:
            self._set_online(True)
            for result in body["results"]:
                if result["status"] == "rejected":
                    log.warning("Server rejected event %s: %s", result["id"], result["reason"])
            self.outbox.remove([r["id"] for r in body["results"]])
            return "sent"
        if status in (401, 403):
            log.error("The server refused this mirror's token. Register it again with "
                      "python -m easyweight.register")
            return "refused"
        if status == 422:  # the batch itself is invalid: a bug, keep it aside
            log.error("The server refused a batch of %d events as invalid: %s", len(events), body)
            self.outbox.bury(events, json.dumps(body))
            return "sent"
        self._set_online(False, f"HTTP {status}")  # 5xx: the server is having trouble
        return "offline"

    def _set_online(self, online, why=None):
        if online and self.online is not True:
            log.info("Connected to %s", self.url)
        elif not online and self.online is not False:
            log.warning("Can't reach the server (%s). Events are kept and sent later", why)
        self.online = online

    def _run(self):
        backoff = self.interval
        while not self._stop.is_set():
            result = self.send_once()
            if result == "sent":
                backoff = self.interval
                continue  # there may be more waiting
            if result == "idle":
                backoff = self.interval
            else:
                backoff = min(self.MAX_BACKOFF, max(backoff * 2, 2))
            self._stop.wait(backoff)

    def start(self):
        self._thread = threading.Thread(target=self._run, name="easyweight-sender", daemon=True)
        self._thread.start()
        return self

    def stop(self, flush_seconds=3):
        """Stop the thread, after trying briefly to send what's left"""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=15)
        deadline = flush_seconds
        while len(self.outbox) and deadline > 0:
            if self.send_once() != "sent":
                break
            deadline -= 1

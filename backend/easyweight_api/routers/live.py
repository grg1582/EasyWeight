"""GET /api/v1/live: a WebSocket that pushes a user's new events as they arrive.

Browsers can't add an Authorization header to a WebSocket, and a token in the
address ends up in logs, so the access token is the first message instead:

    → {"token": "<access token>"}
    ← {"type": "ready"}
    ← {"type": "events", "device": {...}, "events": [...]}   (as they happen)

The connection is closed (code 4401) when the token is wrong, or when it
expires; the dashboard then reconnects with a fresh one.
"""
import asyncio
import contextlib
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ..auth import access_claims
from ..db import get_db
from ..live import hub
from ..models import User

router = APIRouter(tags=["live"])

UNAUTHORIZED = 4401  # like HTTP 401, in the range WebSockets leave to apps
AUTH_SECONDS = 10


def _check(db: Session, token: object) -> tuple[uuid.UUID, float]:
    if not isinstance(token, str):
        raise HTTPException(401, "Not signed in")
    claims = access_claims(token)
    user_id = uuid.UUID(claims["sub"])
    try:
        if db.get(User, user_id) is None:
            raise HTTPException(401, "User no longer exists")
    finally:
        db.close()  # don't hold a database connection for as long as the socket is open
    return user_id, float(claims["exp"])


@router.websocket("/api/v1/live")
async def live(ws: WebSocket, db: Session = Depends(get_db)):
    await ws.accept()
    try:
        first = await asyncio.wait_for(ws.receive_json(), AUTH_SECONDS)
        user_id, expires = await run_in_threadpool(_check, db, first.get("token"))
    except WebSocketDisconnect:
        return
    except (TimeoutError, HTTPException, ValueError, KeyError, AttributeError):
        await ws.close(UNAUTHORIZED, "Not signed in")
        return

    queue = hub.subscribe(user_id)
    try:
        await ws.send_json({"type": "ready"})

        async def send():
            while True:
                await ws.send_json(await queue.get())

        async def receive():  # returns when the dashboard goes away
            with contextlib.suppress(WebSocketDisconnect):
                while True:
                    await ws.receive_text()

        tasks = {asyncio.create_task(send()), asyncio.create_task(receive())}
        done, pending = await asyncio.wait(tasks, timeout=max(0.0, expires - time.time()),
                                           return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        if not done:  # the token expired
            await ws.close(UNAUTHORIZED, "Token expired")
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(user_id, queue)

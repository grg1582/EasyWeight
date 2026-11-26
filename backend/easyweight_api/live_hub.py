"""Live updates: when a device's events are applied, the owner's open
dashboards hear about it right away, over a WebSocket.

The hub lives in the API process, which is enough while the API runs as one
process (as it does on Render). Several processes would pass the messages
through PostgreSQL's LISTEN/NOTIFY or Redis instead.
"""
import asyncio
import uuid

# A dashboard that stops reading misses updates instead of filling memory. It
# loads everything again when it reconnects
QUEUE_SIZE = 100


class LiveHub:
    def __init__(self) -> None:
        self._queues: dict[uuid.UUID, set[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def subscribe(self, user_id: uuid.UUID) -> asyncio.Queue:
        """A queue that gets the user's messages. Call from the event loop"""
        self._loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(QUEUE_SIZE)
        self._queues.setdefault(user_id, set()).add(queue)
        return queue

    def unsubscribe(self, user_id: uuid.UUID, queue: asyncio.Queue) -> None:
        queues = self._queues.get(user_id, set())
        queues.discard(queue)
        if not queues:
            self._queues.pop(user_id, None)

    def listeners(self, user_id: uuid.UUID) -> int:
        return len(self._queues.get(user_id, ()))

    def publish(self, user_id: uuid.UUID, message: dict) -> None:
        """Send a message to the user's open dashboards. Safe to call from the
        worker threads that run the (synchronous) endpoints"""
        loop = self._loop
        if loop is None or user_id not in self._queues or loop.is_closed():
            return
        loop.call_soon_threadsafe(self._deliver, user_id, message)

    def _deliver(self, user_id: uuid.UUID, message: dict) -> None:
        for queue in list(self._queues.get(user_id, ())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass


hub = LiveHub()


def publish_events(device, events, results) -> None:
    """Tell the device's owner about the events that were just applied"""
    if device.owner_id is None:
        return
    applied = {r.id for r in results if r.status == "applied"}
    sent = [e.model_dump(mode="json") for e in events if e.id in applied]
    if sent:
        hub.publish(device.owner_id, {
            "type": "events",
            "device": {"id": str(device.id), "name": device.name, "kind": device.kind},
            "events": sent,
        })

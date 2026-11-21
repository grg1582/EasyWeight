import logging

from fastapi import FastAPI

from .routers import auth, devices, events, health, stats, users, workouts


class _SkipHealthChecks(logging.Filter):
    """Docker calls /health every 10 seconds. Keep those out of the access log"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health " not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_SkipHealthChecks())


def create_app() -> FastAPI:
    app = FastAPI(
        title="EasyWeight API",
        version="0.2.0",
        description="Stores the workouts that EasyWeight mirrors send, and serves "
                    "each user their workout history and stats.\n\n"
                    "Two kinds of sign-in: **User** (email and password, for the "
                    "dashboard) and **Device** (a mirror's token, for sending events).",
    )
    for module in (health, auth, users, devices, events, workouts, stats):
        app.include_router(module.router)
    return app


app = create_app()

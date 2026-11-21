import logging

from fastapi import FastAPI

from .routers import devices, events, health, stats, workouts


class _SkipHealthChecks(logging.Filter):
    """Docker calls /health every 10 seconds. Keep those out of the access log"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health " not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_SkipHealthChecks())


def create_app() -> FastAPI:
    app = FastAPI(
        title="EasyWeight API",
        version="0.1.0",
        description="Stores the workouts that EasyWeight mirrors send, and serves "
                    "workout history and stats.",
    )
    for module in (health, devices, events, workouts, stats):
        app.include_router(module.router)
    return app


app = create_app()

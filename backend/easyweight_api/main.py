import logging

from fastapi import FastAPI

from .config import get_settings
from .routers import auth, devices, events, health, live, pairing, stats, users, workouts


class _SkipHealthChecks(logging.Filter):
    """Docker calls /health every 10 seconds. Keep those out of the access log"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health " not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_SkipHealthChecks())


def _report_errors_to_sentry(dsn: str) -> None:
    import sentry_sdk

    sentry_sdk.init(dsn=dsn, environment=get_settings().environment,
                    traces_sample_rate=0.1, send_default_pii=False)


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.sentry_dsn:
        _report_errors_to_sentry(settings.sentry_dsn)
    app = FastAPI(
        title="EasyWeight API",
        version="0.3.0",
        description="Stores the workouts that EasyWeight mirrors send, and serves "
                    "each user their workout history and stats.\n\n"
                    "Two kinds of sign-in: **User** (email and password, for the "
                    "dashboard) and **Device** (a mirror's token, for sending events).",
    )
    for module in (health, auth, users, devices, pairing, events, workouts, stats, live):
        app.include_router(module.router)
    return app


app = create_app()

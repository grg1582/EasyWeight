from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-secret-change-me-in-production"


class Settings(BaseSettings):
    """Read from environment variables (or a .env file next to where it runs)"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "production" turns on the checks below. Anything else is development
    environment: str = "development"

    database_url: str = "postgresql+psycopg://easyweight:easyweight@localhost:5432/easyweight"
    max_events_per_request: int = 500

    # Signs the login tokens. Anyone who knows it can sign in as anyone, so
    # production refuses to start with the default one
    jwt_secret: str = DEV_JWT_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    # Sign-in attempts allowed per email and address in a time window, so
    # passwords can't be guessed by trying many
    login_attempts: int = 10
    login_window_seconds: int = 300
    # New accounts allowed per address per hour
    signups_per_hour: int = 10

    # The "Try the demo" button: a read-only account with made-up workouts
    demo_enabled: bool = True
    demo_email: str = "demo@easyweight.dev"

    # Error reports to Sentry, when set
    sentry_dsn: str | None = None

    @field_validator("database_url")
    @classmethod
    def _use_psycopg(cls, url: str) -> str:
        # Hosts like Neon and Render give "postgres://..." or "postgresql://...".
        # SQLAlchemy needs to be told which driver to use
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @model_validator(mode="after")
    def _safe_in_production(self) -> "Settings":
        if self.environment == "production" and (
            self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32
        ):
            raise ValueError("Set JWT_SECRET to a long random value (32+ characters) "
                             "in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

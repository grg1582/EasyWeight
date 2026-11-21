from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables (or a .env file next to where it runs)"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://easyweight:easyweight@localhost:5432/easyweight"
    max_events_per_request: int = 500

    # Signs the login tokens. Anyone who knows it can sign in as anyone, so set
    # a long random JWT_SECRET anywhere other than your own computer
    jwt_secret: str = "dev-only-secret-change-me-in-production"
    access_token_minutes: int = 15
    refresh_token_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()

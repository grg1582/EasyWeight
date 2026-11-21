from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from easyweight_api import models  # noqa: F401  (registers the tables)
from easyweight_api.config import get_settings
from easyweight_api.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The tests pass their own database URL; otherwise it comes from the settings
url = config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

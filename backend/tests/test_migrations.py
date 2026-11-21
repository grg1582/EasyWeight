"""The migrations must match models.py and be reversible"""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from conftest import alembic_config
from easyweight_api.db import Base


def test_migrations_match_the_models(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_downgrade_and_upgrade_again(engine):
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), "head")

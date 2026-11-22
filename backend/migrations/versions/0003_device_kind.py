"""device kind

Workouts can now come from the web dashboard too (training with the camera in
the browser). Each user gets one "browser" device for those, next to their
mirrors.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21 16:40:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('devices', sa.Column('kind', sa.String(length=20),
                                       server_default='mirror', nullable=False))
    # At most one browser device per user
    op.create_index('uq_devices_one_browser_per_owner', 'devices', ['owner_id'], unique=True,
                    postgresql_where=sa.text("kind = 'browser'"))


def downgrade():
    op.drop_index('uq_devices_one_browser_per_owner', table_name='devices')
    op.drop_column('devices', 'kind')

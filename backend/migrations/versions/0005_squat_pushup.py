"""squats and push-ups

Two new exercises. They're counted once for the whole body rather than arm
by arm, so a rep's side can now be "both".

PostgreSQL adds enum values in place, but a new value can't be used in the
transaction that added it, so they're added outside one. It can't remove
values, so going back down deletes the squat and push-up sets and builds the
old types again.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-25 20:00:00
"""
from alembic import op


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE exercise ADD VALUE IF NOT EXISTS 'squat'")
        op.execute("ALTER TYPE exercise ADD VALUE IF NOT EXISTS 'pushup'")
        op.execute("ALTER TYPE arm_side ADD VALUE IF NOT EXISTS 'both'")


def _rebuild(type_name, table, column, values):
    op.execute(f"ALTER TYPE {type_name} RENAME TO {type_name}_old")
    op.execute(f"CREATE TYPE {type_name} AS ENUM ({', '.join(repr(v) for v in values)})")
    op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {type_name} "
               f"USING {column}::text::{type_name}")
    op.execute(f"DROP TYPE {type_name}_old")


def downgrade():
    op.execute("DELETE FROM reps WHERE side = 'both'")
    op.execute("DELETE FROM sets WHERE exercise IN ('squat', 'pushup')")  # their reps go too
    _rebuild('exercise', 'sets', 'exercise', ['curl', 'raise', 'press'])
    _rebuild('arm_side', 'reps', 'side', ['left', 'right'])

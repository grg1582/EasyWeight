"""initial tables

Revision ID: 0001
Revises:
Create Date: 2026-11-21 12:25:57.630838
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('devices',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_table('events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_device_id'), 'events', ['device_id'], unique=False)
    op.create_table('workouts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workouts_device_started', 'workouts', ['device_id', 'started_at'], unique=False)
    op.create_table('sets',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workout_id', sa.Uuid(), nullable=False),
    sa.Column('exercise', sa.Enum('curl', 'raise', 'press', name='exercise'), nullable=False),
    sa.Column('set_number', sa.Integer(), nullable=False),
    sa.Column('reps', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sets_workout_id'), 'sets', ['workout_id'], unique=False)
    op.create_table('reps',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('set_id', sa.Uuid(), nullable=False),
    sa.Column('side', sa.Enum('left', 'right', name='arm_side'), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('top', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['set_id'], ['sets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reps_set_id'), 'reps', ['set_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_reps_set_id'), table_name='reps')
    op.drop_table('reps')
    op.drop_index(op.f('ix_sets_workout_id'), table_name='sets')
    op.drop_table('sets')
    op.drop_index('ix_workouts_device_started', table_name='workouts')
    op.drop_table('workouts')
    op.drop_index(op.f('ix_events_device_id'), table_name='events')
    op.drop_table('events')
    op.drop_table('devices')
    sa.Enum(name='arm_side').drop(op.get_bind())
    sa.Enum(name='exercise').drop(op.get_bind())

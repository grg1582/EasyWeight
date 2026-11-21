"""users and refresh tokens

Adds user accounts, their sign-ins (refresh tokens), and an owner for each
device. Devices registered before this have no owner.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21 14:30:13.161450
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('refresh_tokens',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.add_column('devices', sa.Column('owner_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_devices_owner_id'), 'devices', ['owner_id'], unique=False)
    op.create_foreign_key('devices_owner_id_fkey', 'devices', 'users', ['owner_id'], ['id'],
                          ondelete='CASCADE')


def downgrade():
    op.drop_constraint('devices_owner_id_fkey', 'devices', type_='foreignkey')
    op.drop_index(op.f('ix_devices_owner_id'), table_name='devices')
    op.drop_column('devices', 'owner_id')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_table('users')

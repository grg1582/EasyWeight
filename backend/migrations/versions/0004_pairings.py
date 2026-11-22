"""pairings

Connecting a mirror by scanning a QR code. The mirror makes its own token,
asks for a short code and shows it as a QR code; a signed-in user claims the
code, which creates the device with the mirror's token. Only the token's hash
is ever sent or stored.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-22 18:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pairings',
        sa.Column('code', sa.String(length=8), primary_key=True),
        sa.Column('token_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='CASCADE'),
                  nullable=True),
    )


def downgrade():
    op.drop_table('pairings')

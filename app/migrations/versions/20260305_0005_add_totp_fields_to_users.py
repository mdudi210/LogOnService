"""add totp and mfa flags to users

Revision ID: 20260305_0005
Revises: 20260305_0004
Create Date: 2026-03-05 23:55:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0005"
down_revision = "20260305_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("totp_secret", sa.String(length=255), nullable=True))
    op.alter_column("users", "mfa_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "totp_secret")
    op.drop_column("users", "mfa_enabled")

"""add user_agent column to audit logs

Revision ID: 20260305_0004
Revises: 20260305_0003
Create Date: 2026-03-05 23:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0004"
down_revision = "20260305_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_logs", "user_agent")

"""add jti to sessions

Revision ID: 20260305_0003
Revises: 20260302_0002
Create Date: 2026-03-05 22:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0003"
down_revision = "20260302_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("jti", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_sessions_jti"), "sessions", ["jti"], unique=False)

    # Backfill deterministic placeholders for legacy rows.
    op.execute("UPDATE sessions SET jti = id::text WHERE jti IS NULL")

    op.alter_column("sessions", "jti", nullable=False)
    op.create_unique_constraint(op.f("uq_sessions_jti"), "sessions", ["jti"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_sessions_jti"), "sessions", type_="unique")
    op.drop_index(op.f("ix_sessions_jti"), table_name="sessions")
    op.drop_column("sessions", "jti")

"""add jti to sessions

Revision ID: 20260305_0003
Revises: 20260302_0002
Create Date: 2026-03-05 22:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260305_0003"
down_revision = "20260302_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("sessions")}
    indexes = {index["name"] for index in inspector.get_indexes("sessions")}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("sessions")}

    if "jti" not in columns:
        op.add_column("sessions", sa.Column("jti", sa.String(length=255), nullable=True))
        # Backfill deterministic placeholders for legacy rows.
        op.execute("UPDATE sessions SET jti = id::text WHERE jti IS NULL")
        op.alter_column("sessions", "jti", nullable=False)

    if op.f("ix_sessions_jti") not in indexes:
        op.create_index(op.f("ix_sessions_jti"), "sessions", ["jti"], unique=False)

    if op.f("uq_sessions_jti") not in uniques:
        op.create_unique_constraint(op.f("uq_sessions_jti"), "sessions", ["jti"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("sessions")}
    indexes = {index["name"] for index in inspector.get_indexes("sessions")}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("sessions")}

    if op.f("uq_sessions_jti") in uniques:
        op.drop_constraint(op.f("uq_sessions_jti"), "sessions", type_="unique")
    if op.f("ix_sessions_jti") in indexes:
        op.drop_index(op.f("ix_sessions_jti"), table_name="sessions")
    if "jti" in columns:
        op.drop_column("sessions", "jti")

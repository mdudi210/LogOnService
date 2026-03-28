"""add password_salt to user_credentials

Revision ID: 20260302_0002
Revises: 20260227_0001
Create Date: 2026-03-02 11:40:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260302_0002"
down_revision = "20260227_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_credentials")}
    if "password_salt" not in columns:
        op.add_column("user_credentials", sa.Column("password_salt", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_credentials")}
    if "password_salt" in columns:
        op.drop_column("user_credentials", "password_salt")

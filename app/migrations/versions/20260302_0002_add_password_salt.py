"""add password_salt to user_credentials

Revision ID: 20260302_0002
Revises: 20260227_0001
Create Date: 2026-03-02 11:40:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260302_0002"
down_revision = "20260227_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_credentials", sa.Column("password_salt", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("user_credentials", "password_salt")

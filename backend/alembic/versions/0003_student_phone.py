"""student phone number

Revision ID: 0003
Revises: abded17e51b8
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "abded17e51b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("phone", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("students", "phone")

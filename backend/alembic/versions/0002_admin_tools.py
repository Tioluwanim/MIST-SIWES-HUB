"""Demo lifecycle flags and administrative audit trail."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_TABLES = (
    "departments", "units", "users", "siwes_batches", "students",
    "training_programs", "training_classes", "training_materials",
    "training_sessions", "projects", "project_milestones",
    "project_submissions", "announcements",
)


def upgrade() -> None:
    for table in _TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
            batch.create_index("ix_%s_is_demo" % table, ["is_demo"], unique=False)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_admin_user_id", "audit_logs", ["admin_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_admin_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    for table in reversed(_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_index("ix_%s_is_demo" % table)
            batch.drop_column("is_demo")

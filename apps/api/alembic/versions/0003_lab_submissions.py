"""Lab submissions with grading state.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-09

"""
import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False
        ),
        sa.Column("filename", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_lab_submissions_user_id", "lab_submissions", ["user_id"])
    op.create_index("ix_lab_submissions_lesson_id", "lab_submissions", ["lesson_id"])
    op.create_index("ix_lab_submissions_status", "lab_submissions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_lab_submissions_status", table_name="lab_submissions")
    op.drop_index("ix_lab_submissions_lesson_id", table_name="lab_submissions")
    op.drop_index("ix_lab_submissions_user_id", table_name="lab_submissions")
    op.drop_table("lab_submissions")

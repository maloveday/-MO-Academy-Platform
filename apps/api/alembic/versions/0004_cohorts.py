"""Cohorts and cohort assignment on enrollments.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-09

"""
import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cohorts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("starts_on", sa.String(length=10), nullable=True),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("enrollments") as batch:
        batch.add_column(sa.Column("cohort_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_enrollments_cohort_id", "cohorts", ["cohort_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("enrollments") as batch:
        batch.drop_constraint("fk_enrollments_cohort_id", type_="foreignkey")
        batch.drop_column("cohort_id")
    op.drop_table("cohorts")

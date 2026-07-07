"""Initial schema: leads table.

Revision ID: 0001
Revises:
Create Date: 2026-07-07

"""
import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirm_token", sa.String(length=64), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("primer_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_leads_email", "leads", ["email"], unique=True)
    op.create_index("ix_leads_confirm_token", "leads", ["confirm_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_leads_confirm_token", table_name="leads")
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_table("leads")

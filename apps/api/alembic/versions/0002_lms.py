"""LMS: users, magic-link auth, curriculum, progress, quizzes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07

"""
import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_magic_link_tokens_token", "magic_link_tokens", ["token"], unique=True
    )

    op.create_table(
        "session_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_session_tokens_token", "session_tokens", ["token"], unique=True
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_index("ix_courses_slug", "courses", ["slug"], unique=True)

    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.UniqueConstraint("course_id", "number"),
    )

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "module_id", sa.Integer(), sa.ForeignKey("modules.id"), nullable=False
        ),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.UniqueConstraint("module_id", "code"),
    )
    op.create_index("ix_lessons_code", "lessons", ["code"])

    op.create_table(
        "labs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("repo_template_url", sa.String(length=500), nullable=False),
        sa.Column("grading_spec", sa.JSON(), nullable=False),
    )

    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", sa.JSON(), nullable=False),
        sa.Column("correct_index", sa.Integer(), nullable=False),
    )
    op.create_index("ix_quiz_questions_lesson_id", "quiz_questions", ["lesson_id"])

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False
        ),
        sa.Column("tier", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "course_id"),
    )
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"])

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "lesson_id"),
    )
    op.create_index("ix_lesson_progress_user_id", "lesson_progress", ["user_id"])

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quiz_attempts_user_id", "quiz_attempts", ["user_id"])
    op.create_index("ix_quiz_attempts_lesson_id", "quiz_attempts", ["lesson_id"])


def downgrade() -> None:
    for table in (
        "quiz_attempts",
        "lesson_progress",
        "enrollments",
        "quiz_questions",
        "labs",
        "lessons",
        "modules",
        "courses",
        "session_tokens",
        "magic_link_tokens",
        "users",
    ):
        op.drop_table(table)

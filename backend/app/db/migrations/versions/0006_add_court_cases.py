"""add court_cases table

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "court_cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_title",  sa.Text,         nullable=False),
        sa.Column("case_number", sa.String(100),   nullable=True),
        sa.Column("court_name",  sa.Text,          nullable=False),
        sa.Column("case_type",   sa.String(50),    nullable=False, server_default="other"),
        sa.Column("next_date",   sa.Date,          nullable=False),
        sa.Column("description", sa.Text,          nullable=True),
        sa.Column("status",      sa.String(20),    nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_court_cases_user_id",   "court_cases", ["user_id"])
    op.create_index("idx_court_cases_next_date",  "court_cases", ["next_date"])
    op.create_index("idx_court_cases_status",     "court_cases", ["status"])


def downgrade() -> None:
    op.drop_index("idx_court_cases_status",    table_name="court_cases")
    op.drop_index("idx_court_cases_next_date", table_name="court_cases")
    op.drop_index("idx_court_cases_user_id",   table_name="court_cases")
    op.drop_table("court_cases")

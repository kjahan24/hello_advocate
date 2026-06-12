"""add lawyers and lawyer_reviews tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lawyers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name",                sa.Text,             nullable=False),
        sa.Column("email",               sa.Text,             nullable=True),
        sa.Column("phone",               sa.String(20),       nullable=True),
        sa.Column("bar_number",          sa.String(50),       nullable=True, unique=True),
        sa.Column("specializations",     postgresql.JSONB,    nullable=False, server_default="[]"),
        sa.Column("experience_years",    sa.Integer,          nullable=False, server_default="0"),
        sa.Column("fee_per_hour",        sa.Numeric(10, 2),   nullable=True),
        sa.Column("fee_per_consultation",sa.Numeric(10, 2),   nullable=True),
        sa.Column("location",            sa.String(100),      nullable=True),
        sa.Column("bio",                 sa.Text,             nullable=True),
        sa.Column("profile_image_url",   sa.Text,             nullable=True),
        sa.Column("is_verified",         sa.Boolean,          nullable=False, server_default="false"),
        sa.Column("is_available",        sa.Boolean,          nullable=False, server_default="true"),
        sa.Column("rating",              sa.Numeric(3, 2),    nullable=False, server_default="0.00"),
        sa.Column("total_reviews",       sa.Integer,          nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_lawyers_location",     "lawyers", ["location"])
    op.create_index("idx_lawyers_is_verified",  "lawyers", ["is_verified"])
    op.create_index("idx_lawyers_is_available", "lawyers", ["is_available"])

    op.create_table(
        "lawyer_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "lawyer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lawyers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating",  sa.Integer, nullable=False),
        sa.Column("comment", sa.Text,    nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_lawyer_reviews_lawyer_id", "lawyer_reviews", ["lawyer_id"])
    op.create_index("idx_lawyer_reviews_user_id",   "lawyer_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_lawyer_reviews_user_id",   table_name="lawyer_reviews")
    op.drop_index("idx_lawyer_reviews_lawyer_id", table_name="lawyer_reviews")
    op.drop_table("lawyer_reviews")

    op.drop_index("idx_lawyers_is_available", table_name="lawyers")
    op.drop_index("idx_lawyers_is_verified",  table_name="lawyers")
    op.drop_index("idx_lawyers_location",     table_name="lawyers")
    op.drop_table("lawyers")

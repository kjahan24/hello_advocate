"""add subscriptions table

Revision ID: 0004
Revises: 35515012fc21
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "35515012fc21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
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
        sa.Column("plan",           sa.String(20),       nullable=False),
        sa.Column("status",         sa.String(20),       nullable=False, server_default="pending"),
        sa.Column("amount",         sa.Numeric(10, 2),   nullable=False),
        sa.Column("currency",       sa.String(10),       nullable=False, server_default="BDT"),
        sa.Column("transaction_id", sa.String(100),      nullable=False, unique=True),
        sa.Column("ssl_session_id", sa.String(100),      nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("activated_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_subscriptions_user_id",       "subscriptions", ["user_id"])
    op.create_index("idx_subscriptions_status",        "subscriptions", ["status"])
    op.create_index("idx_subscriptions_transaction_id","subscriptions", ["transaction_id"])


def downgrade() -> None:
    op.drop_index("idx_subscriptions_transaction_id", table_name="subscriptions")
    op.drop_index("idx_subscriptions_status",         table_name="subscriptions")
    op.drop_index("idx_subscriptions_user_id",        table_name="subscriptions")
    op.drop_table("subscriptions")

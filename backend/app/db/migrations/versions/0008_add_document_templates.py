"""add document_templates and generated_documents tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("title",       sa.Text,         nullable=False),
        sa.Column("title_en",    sa.String(200),   nullable=True),
        sa.Column("category",    sa.String(50),    nullable=False, server_default="other"),
        sa.Column("description", sa.Text,          nullable=True),
        sa.Column("fields",      postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_pro",      sa.Boolean(),     nullable=False, server_default=sa.false()),
        sa.Column("usage_count", sa.Integer(),     nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_document_templates_category", "document_templates", ["category"])
    op.create_index("idx_document_templates_is_pro",   "document_templates", ["is_pro"])

    op.create_table(
        "generated_documents",
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
            index=True,
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_templates.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("field_values",      postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("generated_content", sa.Text,          nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_generated_docs_user_id",    "generated_documents", ["user_id"])
    op.create_index("idx_generated_docs_template_id", "generated_documents", ["template_id"])


def downgrade() -> None:
    op.drop_index("idx_generated_docs_template_id", table_name="generated_documents")
    op.drop_index("idx_generated_docs_user_id",     table_name="generated_documents")
    op.drop_table("generated_documents")
    op.drop_index("idx_document_templates_is_pro",   table_name="document_templates")
    op.drop_index("idx_document_templates_category", table_name="document_templates")
    op.drop_table("document_templates")

"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Extensions                                                           #
    # ------------------------------------------------------------------ #
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ------------------------------------------------------------------ #
    # acts                                                                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "acts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("act_id", sa.String(20), unique=True, nullable=False),
        sa.Column("title_en", sa.Text, nullable=False),
        sa.Column("title_bn", sa.Text, nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("is_repealed", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("full_text_en", sa.Text, nullable=True),
        sa.Column("full_text_bn", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_acts_act_id", "acts", ["act_id"])
    op.create_index("idx_acts_category", "acts", ["category"])

    # ------------------------------------------------------------------ #
    # sections                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "sections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "act_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("acts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_number", sa.String(20), nullable=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("content_en", sa.Text, nullable=True),
        sa.Column("content_bn", sa.Text, nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_sections_act_id", "sections", ["act_id"])

    # ------------------------------------------------------------------ #
    # cases                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("citation", sa.Text, unique=True, nullable=True),
        sa.Column("court", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("parties", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("related_acts", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # users                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("role", sa.String(20), server_default="citizen", nullable=False),
        sa.Column("plan", sa.String(20), server_default="free", nullable=False),
        sa.Column("query_count_today", sa.Integer, server_default="0", nullable=False),
        sa.Column("query_limit", sa.Integer, server_default="10", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # ------------------------------------------------------------------ #
    # chat_sessions                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "chat_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_chat_sessions_user_id", "chat_sessions", ["user_id"])

    # ------------------------------------------------------------------ #
    # messages                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("sources", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_messages_session_id", "messages", ["session_id"])

    # ------------------------------------------------------------------ #
    # pgvector ivfflat indexes (built AFTER tables are populated in prod) #
    # Requiring at least 1 row; safe to create empty in dev.              #
    # ------------------------------------------------------------------ #
    op.execute(
        "CREATE INDEX idx_acts_embedding ON acts "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX idx_sections_embedding ON sections "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX idx_cases_embedding ON cases "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("chat_sessions")
    op.drop_table("users")
    op.drop_table("cases")
    op.drop_table("sections")
    op.drop_table("acts")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')

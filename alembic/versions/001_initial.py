"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_name", sa.String(200), nullable=False),
        sa.Column("business_url", sa.String(500)),
        sa.Column("owner_name", sa.String(200)),
        sa.Column("owner_email", sa.String(200), index=True),
        sa.Column("owner_initials", sa.String(5)),
        sa.Column("industry", sa.String(100)),
        sa.Column("plan", sa.String(20), server_default="business"),
        sa.Column("status", sa.String(20), server_default="active", index=True),
        sa.Column("api_key", sa.String(64), unique=True),
        sa.Column("avatar_name", sa.String(100), server_default="Aria"),
        sa.Column("primary_color", sa.String(20), server_default="#f59e0b"),
        sa.Column("welcome_message", sa.Text),
        sa.Column("allowed_domains", sa.JSON),
        sa.Column("llm_provider", sa.String(50)),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "knowledge_docs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36),
                  sa.ForeignKey("customers.id", ondelete="CASCADE"), index=True),
        sa.Column("source_name", sa.String(200)),
        sa.Column("doc_type", sa.String(20)),
        sa.Column("chunks_ingested", sa.Integer, server_default="0"),
        sa.Column("char_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36),
                  sa.ForeignKey("customers.id", ondelete="CASCADE"), index=True),
        sa.Column("session_id", sa.String(36), index=True),
        sa.Column("user_message", sa.Text),
        sa.Column("assistant_message", sa.Text),
        sa.Column("rag_latency_ms", sa.Float),
        sa.Column("llm_latency_ms", sa.Float),
        sa.Column("emotion_latency_ms", sa.Float),
        sa.Column("tts_latency_ms", sa.Float),
        sa.Column("viseme_latency_ms", sa.Float),
        sa.Column("total_latency_ms", sa.Float),
        sa.Column("tokens_in", sa.Integer, server_default="0"),
        sa.Column("tokens_out", sa.Integer, server_default="0"),
        sa.Column("sentiment", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), index=True),
    )


def downgrade() -> None:
    op.drop_table("conversations")
    op.drop_table("knowledge_docs")
    op.drop_table("customers")

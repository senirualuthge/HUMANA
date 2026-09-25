"""
humana/app/models/customer.py
ORM models for the HUMANA platform.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Customer (Tenant) ─────────────────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_url: Mapped[Optional[str]] = mapped_column(String(500))
    owner_name: Mapped[Optional[str]] = mapped_column(String(200))
    owner_email: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    owner_initials: Mapped[Optional[str]] = mapped_column(String(5))
    industry: Mapped[Optional[str]] = mapped_column(String(100))

    # Plan: starter | business | enterprise
    plan: Mapped[str] = mapped_column(String(20), default="business")
    # Status: active | paused | suspended
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # API key (generated on creation)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: "hk_" + uuid.uuid4().hex)

    # Avatar config
    avatar_name: Mapped[str] = mapped_column(String(100), default="Aria")
    primary_color: Mapped[str] = mapped_column(String(20), default="#f59e0b")
    welcome_message: Mapped[str] = mapped_column(
        Text, default="Hi! How can I help you today?"
    )
    allowed_domains: Mapped[Optional[List]] = mapped_column(JSON, default=list)

    # LLM override (inherits global if null)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50))
    llm_model: Mapped[Optional[str]] = mapped_column(String(100))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # Relations
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )
    knowledge_docs: Mapped[List["KnowledgeDoc"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


# ── Knowledge Document ────────────────────────────────────────────────────────
class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    source_name: Mapped[str] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(20))  # text | pdf | docx | md | url
    chunks_ingested: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    customer: Mapped["Customer"] = relationship(back_populates="knowledge_docs")


# ── Conversation ──────────────────────────────────────────────────────────────
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    user_message: Mapped[str] = mapped_column(Text)
    assistant_message: Mapped[str] = mapped_column(Text)

    # Latency breakdown (ms)
    rag_latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    llm_latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    emotion_latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    tts_latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    viseme_latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    total_latency_ms: Mapped[Optional[float]] = mapped_column(Float)

    # Token usage
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)

    # Sentiment: positive | neutral | negative
    sentiment: Mapped[Optional[str]] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )

    customer: Mapped["Customer"] = relationship(back_populates="conversations")

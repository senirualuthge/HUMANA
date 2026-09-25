"""
humana/app/models/schemas.py
Pydantic v2 schemas — request bodies, response models, WebSocket messages.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Customer ──────────────────────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_url: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    industry: Optional[str] = None
    plan: str = Field("business", pattern="^(starter|business|enterprise)$")
    avatar_name: str = "Aria"
    primary_color: str = "#f59e0b"
    welcome_message: str = "Hi! How can I help you today?"
    allowed_domains: List[str] = Field(default_factory=list)
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None

    @field_validator("owner_email", mode="before")
    @classmethod
    def validate_email(cls, v):
        if v and "@" not in v:
            raise ValueError("Invalid email address")
        return v


class CustomerUpdate(CustomerCreate):
    business_name: Optional[str] = None  # all fields optional on update


class CustomerResponse(BaseModel):
    id: str
    business_name: str
    business_url: Optional[str]
    owner_name: Optional[str]
    owner_email: Optional[str]
    owner_initials: Optional[str]
    industry: Optional[str]
    plan: str
    status: str
    api_key: str
    avatar_name: str
    primary_color: str
    welcome_message: str
    allowed_domains: Optional[List[str]]
    llm_provider: Optional[str]
    llm_model: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Knowledge ─────────────────────────────────────────────────────────────────
class KnowledgeTextInput(BaseModel):
    text: str = Field(..., min_length=10)
    source_name: str = "Admin Upload"


class KnowledgeIngestResponse(BaseModel):
    message: str
    chunks_ingested: int
    doc_id: str
    source_name: str


class KnowledgeWipeResponse(BaseModel):
    message: str
    customer_id: str


# ── Chat / WebSocket ──────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    """Message sent FROM the browser client over WebSocket."""
    type: str = "message"          # message | ping | config
    text: str = ""
    session_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class PipelineStage(BaseModel):
    name: str
    latency_ms: float
    status: str   # ok | warn | error


class AvatarResponse(BaseModel):
    """Message sent TO the browser client over WebSocket."""
    type: str = "response"         # response | error | connected | ping
    text: str = ""
    audio_base64: Optional[str] = None   # ElevenLabs TTS audio
    visemes: Optional[List[Dict]] = None  # lip-sync frames
    emotion: Optional[str] = None
    pipeline: Optional[List[PipelineStage]] = None
    session_id: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None


# ── Stats / Health ────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    environment: str
    llm_provider: str
    llm_model: str
    active_sessions: int
    db: str
    vector_store: str


class StatsResponse(BaseModel):
    active_sessions: int
    llm_provider: str
    llm_model: str
    total_customers: int
    active_customers: int
    total_conversations_today: int


# ── Analytics ─────────────────────────────────────────────────────────────────
class AnalyticsPeriodResponse(BaseModel):
    period: str
    total_conversations: int
    total_tokens_in: int
    total_tokens_out: int
    estimated_cost_usd: float
    avg_sentiment_positive_pct: float
    avg_latency_ms: float
    per_customer: List[Dict[str, Any]]

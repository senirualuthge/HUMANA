"""
humana/app/api/health.py
Health check, stats, and analytics endpoints used by the admin frontend.

GET /api/health          — system health (DB + vector store + sessions)
GET /api/stats           — platform stats (sessions, LLM config, counts)
GET /api/analytics       — per-customer analytics summary
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import engine, get_db
from app.core.logging import get_logger
from app.models.customer import Conversation, Customer
from app.models.schemas import AnalyticsPeriodResponse, HealthResponse, StatsResponse
from app.services.session_manager import session_manager
from app.services.vector_store import vector_store

log = get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api", tags=["Health & Analytics"])

# Per-provider token cost estimates (USD per token)
_COST_PER_TOKEN = {
    "gpt-4o": {"in": 0.0000025, "out": 0.000010},
    "gpt-4o-mini": {"in": 0.00000015, "out": 0.0000006},
    "claude-sonnet-4-5": {"in": 0.000003, "out": 0.000015},
    "claude-haiku-4-5-20251001": {"in": 0.00000025, "out": 0.00000125},
}

def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = _COST_PER_TOKEN.get(model, {"in": 0.000003, "out": 0.000015})
    return round(tokens_in * rates["in"] + tokens_out * rates["out"], 4)


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    # Test DB
    try:
        await db.execute(select(func.count()).select_from(Customer))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    # Test vector store
    try:
        _ = vector_store._client.list_collections()
        vs_status = "ok"
    except Exception as exc:
        vs_status = f"error: {exc}"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        environment=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        active_sessions=session_manager.active_count,
        db=db_status,
        vector_store=vs_status,
    )


# ── STATS ─────────────────────────────────────────────────────────────────────
@router.get("/stats", response_model=StatsResponse)
async def platform_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Customer)) or 0
    active = await db.scalar(
        select(func.count()).select_from(Customer).where(Customer.status == "active")
    ) or 0
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    convos_today = await db.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.created_at >= today_start)
    ) or 0
    return StatsResponse(
        active_sessions=session_manager.active_count,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        total_customers=total,
        active_customers=active,
        total_conversations_today=convos_today,
    )


# ── ANALYTICS ─────────────────────────────────────────────────────────────────
@router.get("/analytics", response_model=AnalyticsPeriodResponse)
async def analytics(
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period, 7)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # All conversations in window
    convos_q = await db.execute(
        select(Conversation).where(Conversation.created_at >= since)
    )
    convos = convos_q.scalars().all()

    if not convos:
        return AnalyticsPeriodResponse(
            period=period,
            total_conversations=0,
            total_tokens_in=0,
            total_tokens_out=0,
            estimated_cost_usd=0.0,
            avg_sentiment_positive_pct=0.0,
            avg_latency_ms=0.0,
            per_customer=[],
        )

    total_ti = sum(c.tokens_in for c in convos)
    total_to = sum(c.tokens_out for c in convos)
    total_cost = _estimate_cost(settings.llm_model, total_ti, total_to)
    latencies = [c.total_latency_ms for c in convos if c.total_latency_ms]
    avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else 0
    pos_count = sum(1 for c in convos if c.sentiment in ("happy", "excited"))
    avg_pos_pct = round(pos_count / len(convos) * 100, 1) if convos else 0

    # Per customer breakdown
    from collections import defaultdict
    per: Dict[str, Any] = defaultdict(lambda: {
        "conversations": 0, "tokens_in": 0, "tokens_out": 0,
        "positive": 0, "latencies": []
    })
    for c in convos:
        p = per[c.customer_id]
        p["conversations"] += 1
        p["tokens_in"] += c.tokens_in
        p["tokens_out"] += c.tokens_out
        if c.sentiment in ("happy", "excited"):
            p["positive"] += 1
        if c.total_latency_ms:
            p["latencies"].append(c.total_latency_ms)

    # Load customer names
    all_customers_q = await db.execute(select(Customer))
    cust_map = {c.id: c for c in all_customers_q.scalars().all()}

    per_customer_list: List[Dict[str, Any]] = []
    for cid, data in per.items():
        c = cust_map.get(cid)
        lats = data["latencies"]
        per_customer_list.append({
            "customer_id": cid,
            "business_name": c.business_name if c else cid,
            "plan": c.plan if c else "unknown",
            "conversations": data["conversations"],
            "tokens_in": data["tokens_in"],
            "tokens_out": data["tokens_out"],
            "estimated_cost_usd": _estimate_cost(settings.llm_model, data["tokens_in"], data["tokens_out"]),
            "sentiment_positive_pct": round(data["positive"] / max(data["conversations"], 1) * 100, 1),
            "avg_latency_ms": round(sum(lats) / len(lats), 1) if lats else 0,
        })

    per_customer_list.sort(key=lambda x: x["estimated_cost_usd"], reverse=True)

    return AnalyticsPeriodResponse(
        period=period,
        total_conversations=len(convos),
        total_tokens_in=total_ti,
        total_tokens_out=total_to,
        estimated_cost_usd=total_cost,
        avg_sentiment_positive_pct=avg_pos_pct,
        avg_latency_ms=avg_lat,
        per_customer=per_customer_list,
    )

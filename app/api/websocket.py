"""
humana/app/api/websocket.py
WebSocket endpoint: ws://localhost:8000/ws/avatar/{business_id}

Protocol (JSON frames):
  CLIENT → SERVER
    { "type": "message", "text": "...", "session_id": "..." }
    { "type": "ping" }

  SERVER → CLIENT
    { "type": "connected", "session_id": "...", "avatar_name": "...", "welcome_message": "..." }
    { "type": "response", "text": "...", "audio_base64": "...", "visemes": [...],
      "emotion": "...", "pipeline": [...], "latency_ms": 420, "tokens_in": 120, "tokens_out": 85 }
    { "type": "error", "text": "..." }
    { "type": "pong" }
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.customer import Conversation, Customer
from app.models.schemas import ChatMessage
from app.pipeline.avatar_pipeline import PipelineContext, run_pipeline
from app.services.session_manager import session_manager

log = get_logger(__name__)
router = APIRouter(tags=["WebSocket"])

# In-memory conversation history per session (keyed by session_id)
# In production consider Redis for multi-worker deployments
_histories: Dict[str, List[Dict[str, str]]] = {}


@router.websocket("/ws/avatar/{business_id}")
async def avatar_websocket(ws: WebSocket, business_id: str):
    session_id = str(uuid.uuid4())
    log.info("ws_incoming", business_id=business_id, session_id=session_id)

    # Load customer from DB
    async with AsyncSessionLocal() as db:
        customer: Customer | None = await db.get(Customer, business_id)

    if not customer:
        await ws.close(code=4004, reason="Business not found")
        return
    if customer.status != "active":
        await ws.close(code=4003, reason="Business account is inactive")
        return

    session = await session_manager.connect(ws, business_id, session_id)
    _histories[session_id] = []

    # Send connection confirmation
    await session.send({
        "type": "connected",
        "session_id": session_id,
        "avatar_name": customer.avatar_name,
        "primary_color": customer.primary_color,
        "welcome_message": customer.welcome_message,
    })

    try:
        while True:
            raw = await ws.receive_json()
            msg = ChatMessage.model_validate(raw)

            # ── Ping ──────────────────────────────────────────────────────────
            if msg.type == "ping":
                await session.send({"type": "pong"})
                session.last_ping = datetime.now(timezone.utc)
                continue

            # ── Chat message ──────────────────────────────────────────────────
            if msg.type == "message" and msg.text.strip():
                session.message_count += 1

                ctx = PipelineContext(
                    business_id=business_id,
                    session_id=session_id,
                    user_message=msg.text.strip(),
                    history=list(_histories[session_id]),
                    avatar_name=customer.avatar_name,
                    welcome_message=customer.welcome_message,
                    llm_provider=customer.llm_provider,
                    llm_model=customer.llm_model,
                )

                # Run the full pipeline
                response = await run_pipeline(ctx)

                # Update history
                _histories[session_id].append({"role": "user", "content": msg.text})
                _histories[session_id].append({"role": "assistant", "content": ctx.assistant_text})
                # Keep last 20 turns in memory
                _histories[session_id] = _histories[session_id][-40:]

                # Persist conversation to DB
                async with AsyncSessionLocal() as db:
                    convo = Conversation(
                        customer_id=business_id,
                        session_id=session_id,
                        user_message=msg.text,
                        assistant_message=ctx.assistant_text,
                        rag_latency_ms=next((s.latency_ms for s in ctx.stages if s.name == "RAG"), None),
                        llm_latency_ms=next((s.latency_ms for s in ctx.stages if s.name == "LLM"), None),
                        emotion_latency_ms=next((s.latency_ms for s in ctx.stages if s.name == "Emotion"), None),
                        tts_latency_ms=next((s.latency_ms for s in ctx.stages if s.name == "TTS"), None),
                        viseme_latency_ms=next((s.latency_ms for s in ctx.stages if s.name == "Viseme"), None),
                        total_latency_ms=response.latency_ms,
                        tokens_in=ctx.tokens_in,
                        tokens_out=ctx.tokens_out,
                        sentiment=ctx.emotion,
                    )
                    db.add(convo)
                    await db.commit()

                # Send response back over WS
                await session.send(response.model_dump(exclude_none=True))
                log.info("ws_turn_complete", session_id=session_id,
                         latency_ms=response.latency_ms, emotion=ctx.emotion)

    except WebSocketDisconnect:
        log.info("ws_disconnected_clean", session_id=session_id)
    except Exception as exc:
        log.error("ws_error", session_id=session_id, error=str(exc))
        try:
            await ws.send_json({"type": "error", "text": "An internal error occurred"})
        except Exception:
            pass
    finally:
        await session_manager.disconnect(session_id)
        _histories.pop(session_id, None)

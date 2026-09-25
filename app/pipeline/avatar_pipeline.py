"""
humana/app/pipeline/avatar_pipeline.py

The full HUMANA avatar response pipeline:

  User message
       │
  ┌────▼────┐
  │  Stage 1 │  RAG — retrieve relevant KB chunks
  └────┬────┘
       │ context docs
  ┌────▼────┐
  │  Stage 2 │  LLM — generate response (OpenAI / Anthropic)
  └────┬────┘
       │ assistant text
  ┌────▼────┐
  │  Stage 3 │  Emotion — classify emotion tag from response
  └────┬────┘
       │ emotion label
  ┌────▼────┐
  │  Stage 4 │  TTS — synthesise speech (ElevenLabs / none)
  └────┬────┘
       │ audio bytes + visemes
  ┌────▼────┐
  │  Stage 5 │  Viseme — generate lip-sync frame timestamps
  └────┴────┘
       │
  AvatarResponse (JSON → WebSocket)

Each stage records its own latency and produces a PipelineStage metric.
"""
from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import AvatarResponse, PipelineStage
from app.services.vector_store import vector_store

log = get_logger(__name__)
settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


@dataclass
class PipelineContext:
    """Mutable bag-of-state passed through every stage."""
    business_id: str
    session_id: str
    user_message: str
    history: List[Dict[str, str]] = field(default_factory=list)
    # Filled in by stages
    rag_docs: List[str] = field(default_factory=list)
    assistant_text: str = ""
    emotion: str = "neutral"
    audio_bytes: Optional[bytes] = None
    visemes: Optional[List[Dict]] = None
    tokens_in: int = 0
    tokens_out: int = 0
    stages: List[PipelineStage] = field(default_factory=list)
    # Avatar config (injected from customer record)
    avatar_name: str = "Aria"
    welcome_message: str = "Hi! How can I help you today?"
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — RAG Retrieval
# ══════════════════════════════════════════════════════════════════════════════
async def stage_rag(ctx: PipelineContext) -> PipelineStage:
    t = time.perf_counter()
    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: vector_store.query(ctx.business_id, ctx.user_message),
        )
        ctx.rag_docs = [doc for doc, _, _ in results]
        lat = _ms(t)
        status = "warn" if lat > 300 else "ok"
        log.debug("rag_stage", business_id=ctx.business_id,
                  docs=len(ctx.rag_docs), latency_ms=lat)
        return PipelineStage(name="RAG", latency_ms=lat, status=status)
    except Exception as exc:
        lat = _ms(t)
        log.error("rag_stage_failed", error=str(exc))
        ctx.rag_docs = []
        return PipelineStage(name="RAG", latency_ms=lat, status="error")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — LLM Generation
# ══════════════════════════════════════════════════════════════════════════════
def _build_system_prompt(ctx: PipelineContext) -> str:
    kb_context = "\n\n".join(ctx.rag_docs) if ctx.rag_docs else ""
    kb_block = (
        f"\n\n--- Knowledge Base Context ---\n{kb_context}\n--- End Context ---"
        if kb_context
        else ""
    )
    return (
        f"You are {ctx.avatar_name}, a friendly and knowledgeable virtual assistant. "
        f"Answer questions accurately and concisely. "
        f"If the answer is in the provided context, use it. "
        f"If not, use your general knowledge but stay on-topic."
        f"{kb_block}"
    )


async def _call_openai(ctx: PipelineContext, system: str) -> tuple[str, int, int]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    model = ctx.llm_model or settings.llm_model
    messages = [{"role": "system", "content": system}]
    messages += ctx.history[-8:]  # last 4 turns
    messages.append({"role": "user", "content": ctx.user_message})
    resp = await client.chat.completions.create(
        model=model, messages=messages, max_tokens=600, temperature=0.7
    )
    text = resp.choices[0].message.content or ""
    return text, resp.usage.prompt_tokens, resp.usage.completion_tokens


async def _call_anthropic(ctx: PipelineContext, system: str) -> tuple[str, int, int]:
    import anthropic as ant
    client = ant.AsyncAnthropic(api_key=settings.anthropic_api_key)
    model = ctx.llm_model or settings.llm_model
    messages = list(ctx.history[-8:])
    messages.append({"role": "user", "content": ctx.user_message})
    resp = await client.messages.create(
        model=model,
        system=system,
        messages=messages,
        max_tokens=600,
    )
    text = resp.content[0].text if resp.content else ""
    return text, resp.usage.input_tokens, resp.usage.output_tokens


async def stage_llm(ctx: PipelineContext) -> PipelineStage:
    t = time.perf_counter()
    system = _build_system_prompt(ctx)
    provider = ctx.llm_provider or settings.llm_provider
    try:
        if provider == "anthropic":
            text, ti, to = await _call_anthropic(ctx, system)
        else:
            text, ti, to = await _call_openai(ctx, system)
        ctx.assistant_text = text
        ctx.tokens_in = ti
        ctx.tokens_out = to
        lat = _ms(t)
        status = "warn" if lat > 2000 else "ok"
        log.debug("llm_stage", provider=provider, tokens_in=ti,
                  tokens_out=to, latency_ms=lat)
        return PipelineStage(name="LLM", latency_ms=lat, status=status)
    except Exception as exc:
        lat = _ms(t)
        log.error("llm_stage_failed", provider=provider, error=str(exc))
        ctx.assistant_text = (
            "I'm sorry, I'm having trouble responding right now. Please try again."
        )
        return PipelineStage(name="LLM", latency_ms=lat, status="error")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — Emotion Classification
# ══════════════════════════════════════════════════════════════════════════════
_EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "happy": ["great", "wonderful", "fantastic", "glad", "happy", "excellent", "delighted", "pleased"],
    "sad": ["sorry", "unfortunately", "regret", "apologize", "sad", "difficult"],
    "excited": ["amazing", "incredible", "awesome", "wow", "exciting", "can't wait"],
    "concerned": ["careful", "warning", "attention", "important", "caution", "please note"],
    "thinking": ["let me", "consider", "thinking", "analyzing", "processing", "one moment"],
}


async def stage_emotion(ctx: PipelineContext) -> PipelineStage:
    t = time.perf_counter()
    text_lower = ctx.assistant_text.lower()
    detected = "neutral"
    for emotion, keywords in _EMOTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            detected = emotion
            break
    ctx.emotion = detected
    lat = _ms(t)
    log.debug("emotion_stage", emotion=detected, latency_ms=lat)
    return PipelineStage(name="Emotion", latency_ms=lat, status="ok")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — TTS (ElevenLabs)
# ══════════════════════════════════════════════════════════════════════════════
async def stage_tts(ctx: PipelineContext) -> PipelineStage:
    t = time.perf_counter()
    if not settings.elevenlabs_api_key:
        lat = _ms(t)
        log.debug("tts_stage_skipped", reason="no_api_key")
        return PipelineStage(name="TTS", latency_ms=lat, status="ok")
    try:
        from elevenlabs import AsyncElevenLabs
        client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
        audio_gen = await client.generate(
            text=ctx.assistant_text,
            voice=settings.elevenlabs_voice_id,
            model="eleven_turbo_v2",
        )
        # Collect async generator
        chunks = []
        async for chunk in audio_gen:
            chunks.append(chunk)
        ctx.audio_bytes = b"".join(chunks)
        lat = _ms(t)
        status = "warn" if lat > 1500 else "ok"
        log.debug("tts_stage", bytes=len(ctx.audio_bytes), latency_ms=lat)
        return PipelineStage(name="TTS", latency_ms=lat, status=status)
    except Exception as exc:
        lat = _ms(t)
        log.error("tts_stage_failed", error=str(exc))
        return PipelineStage(name="TTS", latency_ms=lat, status="error")


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — Viseme (lip-sync frame generation)
# ══════════════════════════════════════════════════════════════════════════════
# Simple phoneme→viseme mapping (CMU ARPAbet-inspired)
_PHONEME_VISEME: Dict[str, str] = {
    "a": "AA", "e": "EH", "i": "IH", "o": "OW", "u": "UW",
    "b": "PP", "p": "PP", "m": "PP",
    "f": "FF", "v": "FF",
    "th": "TH",
    "d": "DD", "t": "DD", "n": "DD",
    "k": "kk", "g": "kk",
    "s": "SS", "z": "SS",
    "sh": "CH", "ch": "CH",
    "l": "nn", "r": "RR",
    "w": "WW", "y": "WW",
    "h": "SS",
}


def _text_to_visemes(text: str) -> List[Dict]:
    """
    Naive viseme timeline generator.
    In production replace with proper phoneme aligner or ElevenLabs viseme API.
    ~120 words/min → ~0.5s/word → ~0.07s/phoneme
    """
    words = text.split()
    frames = []
    t = 0.0
    for word in words:
        word_clean = word.lower().strip(".,!?;:")
        i = 0
        while i < len(word_clean):
            ch = word_clean[i]
            if i + 1 < len(word_clean) and word_clean[i : i + 2] in _PHONEME_VISEME:
                viseme = _PHONEME_VISEME[word_clean[i : i + 2]]
                i += 2
            elif ch in _PHONEME_VISEME:
                viseme = _PHONEME_VISEME[ch]
                i += 1
            else:
                viseme = "sil"
                i += 1
            frames.append({"t": round(t, 3), "v": viseme})
            t += 0.065
        t += 0.05  # inter-word gap
    frames.append({"t": round(t, 3), "v": "sil"})
    return frames


async def stage_viseme(ctx: PipelineContext) -> PipelineStage:
    t = time.perf_counter()
    ctx.visemes = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _text_to_visemes(ctx.assistant_text)
    )
    lat = _ms(t)
    log.debug("viseme_stage", frames=len(ctx.visemes or []), latency_ms=lat)
    return PipelineStage(name="Viseme", latency_ms=lat, status="ok")


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
async def run_pipeline(ctx: PipelineContext) -> AvatarResponse:
    """
    Execute all five stages sequentially, collecting latency metrics.
    Returns AvatarResponse ready to send over WebSocket.
    """
    t_total = time.perf_counter()

    # Stages run in order; each awaits the previous
    rag_stage = await stage_rag(ctx)
    llm_stage = await stage_llm(ctx)

    # Emotion + TTS + Viseme can overlap (but viseme needs text from LLM)
    emotion_stage, tts_stage, viseme_stage = await asyncio.gather(
        stage_emotion(ctx),
        stage_tts(ctx),
        stage_viseme(ctx),
    )

    ctx.stages = [rag_stage, llm_stage, emotion_stage, tts_stage, viseme_stage]
    total_ms = _ms(t_total)

    audio_b64 = (
        base64.b64encode(ctx.audio_bytes).decode() if ctx.audio_bytes else None
    )

    return AvatarResponse(
        type="response",
        text=ctx.assistant_text,
        audio_base64=audio_b64,
        visemes=ctx.visemes,
        emotion=ctx.emotion,
        pipeline=ctx.stages,
        session_id=ctx.session_id,
        latency_ms=total_ms,
        tokens_in=ctx.tokens_in,
        tokens_out=ctx.tokens_out,
    )

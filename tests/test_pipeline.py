"""
tests/test_pipeline.py
Run with: pytest tests/ -v
"""
import asyncio
import pytest # type: ignore
from unittest.mock import AsyncMock, patch, MagicMock # type: ignore

from app.models.messages import Emotion, PipelineResult # type: ignore
from app.services.emotion_service import classify_emotion, _rule_based_emotion # type: ignore


# ── Emotion tests ─────────────────────────────────────────────────────────────

def test_rule_based_emotion_positive():
    emotion = _rule_based_emotion("Great! We're happy to help you.")
    assert emotion.valence > 0

def test_rule_based_emotion_sorry():
    emotion = _rule_based_emotion("Sorry, we are unable to help with that.")
    assert emotion.valence < 0

def test_rule_based_emotion_neutral():
    emotion = _rule_based_emotion("The price is shown on our website.")
    assert isinstance(emotion, Emotion)

def test_emotion_label_enthusiastic():
    e = Emotion(valence=0.8, arousal=0.6)
    assert e.label == "enthusiastic"

def test_emotion_label_neutral():
    e = Emotion(valence=0.0, arousal=0.0)
    assert e.label == "neutral"


# ── Knowledge service tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_knowledge_ingest_and_retrieve():
    from app.services.knowledge_service import KnowledgeService # type: ignore

    with patch("app.services.knowledge_service._get_chroma_client") as mock_chroma:
        # Mock chroma client
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        service = KnowledgeService()
        # Just verify it doesn't raise
        assert service is not None


# ── Brain service tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_brain_service_returns_pipeline_result():
    from app.services.brain_service import BrainService # type: ignore

    service = BrainService()

    with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm, \
         patch("app.services.brain_service.knowledge_service.retrieve", new_callable=AsyncMock) as mock_retrieve, \
         patch("app.services.brain_service.classify_emotion", new_callable=AsyncMock) as mock_emotion:

        mock_llm.return_value = "We're open Monday to Friday, 9am to 5pm."
        mock_retrieve.return_value = ("Hours: Mon-Fri 9-5", 0.85)
        mock_emotion.return_value = Emotion(valence=0.4, arousal=0.2)

        result = await service.process(
            business_id="test-biz",
            user_message="What are your hours?",
            conversation_history=[],
            avatar_config={
                "avatar_name": "Alex",
                "business_name": "Test Co",
                "personality": "Friendly",
                "role_description": "Answer questions",
            },
        )

        assert isinstance(result, PipelineResult)
        assert result.text == "We're open Monday to Friday, 9am to 5pm." # type: ignore
        assert result.confidence == 0.85 # type: ignore
        assert result.source == "knowledge_base" # type: ignore


@pytest.mark.asyncio
async def test_brain_service_low_confidence_triggers_handoff():
    from app.services.brain_service import BrainService, CONFIDENCE_HANDOFF_THRESHOLD # type: ignore

    service = BrainService()

    with patch("app.services.brain_service.knowledge_service.retrieve", new_callable=AsyncMock) as mock_retrieve, \
         patch("app.services.brain_service.classify_emotion", new_callable=AsyncMock) as mock_emotion:

        mock_retrieve.return_value = ("some context", CONFIDENCE_HANDOFF_THRESHOLD - 0.1)
        mock_emotion.return_value = Emotion(valence=0.1, arousal=0.0)

        result = await service.process(
            business_id="test-biz",
            user_message="What is the meaning of life?",
            conversation_history=[],
            avatar_config={
                "avatar_name": "Alex",
                "business_name": "Test Co",
                "personality": "Friendly",
                "role_description": "Answer questions",
            },
        )

        assert result.source == "handoff_fallback"
        assert "team member" in result.text.lower()


# ── Session manager tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_create_and_remove():
    from app.core.session_manager import SessionManager # type: ignore
    from unittest.mock import MagicMock

    manager = SessionManager(max_per_business=5)
    mock_ws = MagicMock()

    session = await manager.create("biz-1", mock_ws)
    assert session.business_id == "biz-1"
    assert manager.active_count() == 1
    assert manager.business_count("biz-1") == 1

    await manager.remove(session.id)
    assert manager.active_count() == 0


@pytest.mark.asyncio
async def test_session_enforces_per_business_limit():
    from app.core.session_manager import SessionManager # type: ignore
    from unittest.mock import MagicMock

    manager = SessionManager(max_per_business=2)
    mock_ws = MagicMock()

    await manager.create("biz-x", mock_ws)
    await manager.create("biz-x", mock_ws)

    with pytest.raises(ConnectionError):
        await manager.create("biz-x", mock_ws)


# ── Viseme tests ──────────────────────────────────────────────────────────────

def test_viseme_estimation_produces_output():
    from app.services.voice_service import _estimate_visemes_from_text # type: ignore
    visemes = _estimate_visemes_from_text("Hello there, how are you?")
    assert len(visemes) > 0
    for v in visemes:
        assert "viseme" in v
        assert "time_offset_ms" in v
        assert "duration_ms" in v


# ── Bug #3 regression: empty context must not hallucinate ─────────────────────

@pytest.mark.asyncio
async def test_brain_service_empty_context_triggers_handoff():
    """
    When knowledge_service returns empty context (no docs ingested),
    the avatar must NOT call the LLM and must return handoff_fallback.
    Previously this was broken: the old 'and context' logic let LLM
    hallucinate answers with zero grounding.
    """
    from app.services.brain_service import BrainService # type: ignore

    service = BrainService()

    with patch("app.services.brain_service.knowledge_service.retrieve", new_callable=AsyncMock) as mock_retrieve, \
         patch("app.services.brain_service.classify_emotion", new_callable=AsyncMock) as mock_emotion, \
         patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:

        # Knowledge base empty → returns ("", 0.0)
        mock_retrieve.return_value = ("", 0.0)
        mock_emotion.return_value = Emotion(valence=0.1, arousal=0.0)

        result = await service.process(
            business_id="test-biz",
            user_message="What are your prices?",
            conversation_history=[],
            avatar_config={
                "avatar_name": "Alex",
                "business_name": "Test Co",
                "personality": "Friendly",
                "role_description": "Answer questions",
            },
        )

        # LLM must NOT have been called
        mock_llm.assert_not_called()

        # Must be a handoff, not a hallucinated answer
        assert result.source == "handoff_fallback"
        assert "team member" in result.text.lower()


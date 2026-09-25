"""
conversation-service/app/swarm/agents/intent.py
LLM-powered intent classification agent.

V1: Checked for "?" character to decide intent.
V3: Uses GPT-4o-mini structured JSON output to classify into 7 intent categories
    with a confidence score, enabling intelligent downstream routing.
"""
import json
import os
from typing import Optional
from langchain_core.messages import AIMessage
from openai import AsyncOpenAI
from ..state import AgentState

_client: Optional[AsyncOpenAI] = None

VALID_INTENTS = [
    "purchase_decision",
    "pricing_inquiry",
    "general_knowledge",
    "support_request",
    "booking_request",
    "objection",
    "general_conversation",
]

CLASSIFICATION_PROMPT = """You are an intent classifier for a business AI assistant.
Classify the user's message into exactly ONE of these intents:
- purchase_decision: User is ready to buy, comparing options, or asking "how to get started"
- pricing_inquiry: Asking about costs, plans, pricing tiers
- general_knowledge: Asking factual questions about the business, products, or services
- support_request: Reporting a problem, asking for help with an existing issue
- booking_request: Wanting to schedule a demo, appointment, or meeting
- objection: Expressing doubt, hesitation, or pushback ("too expensive", "not sure", "compared to X")
- general_conversation: Greetings, small talk, off-topic, or unclear intent

Return ONLY a JSON object:
{"intent": "<one_of_above>", "confidence": <0.0-1.0>}
"""


def _get_client() -> Optional[AsyncOpenAI]:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            _client = AsyncOpenAI(api_key=api_key)
    return _client


async def intent_agent(state: AgentState) -> dict:
    if not state.get("messages"):
        return {"messages": [], "intent": "general_conversation", "intent_confidence": 0.0}

    last_message = state["messages"][-1].content
    client = _get_client()

    if not client:
        # Fallback to simple heuristic when no API key
        intent = _heuristic_classify(last_message)
        return {
            "messages": [AIMessage(content=f"[IntentAgent] Classified: {intent} (heuristic)")],
            "intent": intent,
            "intent_confidence": 0.5,
        }

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": last_message[:500]},
            ],
            max_tokens=60,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        intent = data.get("intent", "general_conversation")
        confidence = float(data.get("confidence", 0.5))

        # Validate intent is one of the allowed values
        if intent not in VALID_INTENTS:
            intent = "general_conversation"
            confidence = 0.3

    except Exception:
        intent = _heuristic_classify(last_message)
        confidence = 0.4

    return {
        "messages": [AIMessage(content=f"[IntentAgent] Classified: {intent} (conf={confidence:.2f})")],
        "intent": intent,
        "intent_confidence": confidence,
    }


def _heuristic_classify(text: str) -> str:
    """Fast keyword-based fallback when LLM is unavailable."""
    text_lower = text.lower()

    price_words = {"price", "cost", "pricing", "plan", "tier", "fee", "charge", "expensive", "cheap"}
    book_words = {"book", "schedule", "appointment", "demo", "meeting", "call", "calendar"}
    buy_words = {"buy", "purchase", "subscribe", "sign up", "get started", "order", "checkout"}
    support_words = {"help", "issue", "problem", "broken", "error", "fix", "not working", "bug"}
    objection_words = {"but", "however", "not sure", "too expensive", "competitor", "alternative"}

    words = set(text_lower.split())

    if words & buy_words:
        return "purchase_decision"
    if words & price_words:
        return "pricing_inquiry"
    if words & book_words:
        return "booking_request"
    if words & support_words:
        return "support_request"
    if words & objection_words:
        return "objection"
    if "?" in text:
        return "general_knowledge"

    return "general_conversation"

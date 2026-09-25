"""
conversation-service/app/swarm/agents/sales.py
Lead scoring + strategy-aware CTA injection.

V1: Appended hardcoded "Would you like to book a demo?" to every message.
V3: Computes a lead_score from intent, engagement signals, and history.
    Selects one of three strategy tiers and injects a contextual CTA.
"""
from langchain_core.messages import AIMessage
from ..state import AgentState

# ── Lead scoring weights ──────────────────────────────────────────────────────

INTENT_SCORES: dict[str, float] = {
    "purchase_decision": 0.40,
    "pricing_inquiry": 0.30,
    "booking_request": 0.35,
    "objection": 0.20,     # interested enough to object
    "general_knowledge": 0.10,
    "support_request": 0.05,
    "general_conversation": 0.0,
}

# ── Strategy tiers ────────────────────────────────────────────────────────────

STRATEGY_EDUCATE = "educate"       # score < 0.3 — nurture, add value
STRATEGY_COMPARE = "compare"       # 0.3 – 0.6 — differentiate, overcome objections
STRATEGY_CLOSE = "close"           # > 0.6 — push for conversion


def _compute_lead_score(state: AgentState) -> float:
    """
    Multi-signal lead scoring:
      - intent (0–0.40)
      - message length (0–0.10): longer messages = more engaged
      - question count (0–0.10): questions = interest
      - conversation depth (0–0.15): more turns = higher commitment
      - prior score carry (0–0.25): momentum from prior messages
    """
    score = 0.0

    # 1. Intent signal
    intent = state.get("intent", "general_conversation")
    score += INTENT_SCORES.get(intent, 0.0)

    # 2. Messages analysis
    messages = state.get("messages", [])
    user_messages = [m for m in messages if getattr(m, "type", "") == "human"]

    if user_messages:
        last_msg = user_messages[-1].content if user_messages else ""

        # Message length signal (normalized: 200 chars = full 0.10)
        length_score = min(len(last_msg) / 200.0, 1.0) * 0.10
        score += length_score

        # Question count signal
        question_count = last_msg.count("?")
        score += min(question_count * 0.05, 0.10)

    # 3. Conversation depth (normalized: 10 turns = full 0.15)
    depth = len(user_messages)
    score += min(depth / 10.0, 1.0) * 0.15

    # 4. Carry forward prior score with decay
    prior_score = state.get("lead_score", 0.0)
    score += prior_score * 0.25

    return min(1.0, round(score, 3))


def _select_strategy(score: float) -> str:
    if score >= 0.6:
        return STRATEGY_CLOSE
    if score >= 0.3:
        return STRATEGY_COMPARE
    return STRATEGY_EDUCATE


def _generate_cta(strategy: str, intent: str) -> str:
    """Return a contextual call-to-action based on strategy tier and intent."""
    if strategy == STRATEGY_CLOSE:
        if intent == "booking_request":
            return "Great timing — I can set up a personalized demo for you right now. What time works best?"
        if intent == "purchase_decision":
            return "You're all set to get started! Want me to walk you through the quick setup?"
        return "Ready to take the next step? I can connect you with our team to get started today."

    if strategy == STRATEGY_COMPARE:
        if intent == "pricing_inquiry":
            return "Would you like me to break down which plan fits your needs best?"
        if intent == "objection":
            return "Those are fair points. Want to see how we compare on the areas that matter most to you?"
        return "Curious how this works in practice? I can share a quick case study that might help."

    # EDUCATE
    if intent == "general_knowledge":
        return "Want me to dive deeper into any of these details?"
    return "Is there anything specific you'd like to know more about?"


async def sales_agent(state: AgentState) -> dict:
    if not state.get("messages"):
        return {"messages": [], "lead_score": 0.0}

    # Compute lead score
    lead_score = _compute_lead_score(state)
    strategy = _select_strategy(lead_score)
    intent = state.get("intent", "general_conversation")

    # Generate contextual CTA
    cta = _generate_cta(strategy, intent)

    return {
        "messages": [
            AIMessage(
                content=(
                    f"[SalesAgent] Lead score: {lead_score:.2f} | "
                    f"Strategy: {strategy} | CTA: {cta}"
                )
            )
        ],
        "lead_score": lead_score,
    }

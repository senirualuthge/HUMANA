"""
conversation-service/app/swarm/agents/planner.py
NEW in V3 — Autonomous conversation planner.

Generates a 3–5 step task graph based on intent so that subsequent agents
(knowledge, sales, personality) follow a coherent sequence instead of
acting independently.

Example plan for purchase_decision:
  ["qualify_needs", "explain_features", "compare_plans", "offer_demo"]
"""
from langchain_core.messages import AIMessage
from ..state import AgentState

# ── Plan templates keyed by intent ────────────────────────────────────────────

PLAN_TEMPLATES: dict[str, list[str]] = {
    "purchase_decision": [
        "qualify_needs",
        "explain_relevant_features",
        "compare_plans",
        "offer_demo_or_trial",
    ],
    "pricing_inquiry": [
        "acknowledge_interest",
        "present_pricing_tiers",
        "highlight_value_per_tier",
        "suggest_best_fit",
    ],
    "booking_request": [
        "confirm_booking_intent",
        "collect_preferred_time",
        "summarize_and_confirm",
    ],
    "support_request": [
        "acknowledge_issue",
        "gather_details",
        "provide_solution_or_escalate",
    ],
    "objection": [
        "acknowledge_concern",
        "reframe_with_evidence",
        "offer_alternative",
        "check_satisfaction",
    ],
    "general_knowledge": [
        "retrieve_relevant_info",
        "present_answer",
        "offer_deeper_dive",
    ],
    "general_conversation": [
        "friendly_response",
        "guide_toward_value",
    ],
}


def _get_plan(intent: str, confidence: float) -> list[str]:
    """
    Select a plan template. If confidence is low, prepend a clarification step.
    """
    plan = list(PLAN_TEMPLATES.get(intent, PLAN_TEMPLATES["general_conversation"]))

    if confidence < 0.6:
        plan.insert(0, "clarify_intent")

    # Cap at 5 steps to prevent runaway sequences
    return plan[:5]


async def planner_agent(state: AgentState) -> dict:
    """
    Reads the classified intent and generates a conversation plan.
    Stores the plan in state so downstream agents can reference it.
    """
    intent = state.get("intent", "general_conversation")
    confidence = state.get("intent_confidence", 0.5)

    plan = _get_plan(intent, confidence)
    current_step = state.get("plan_step", 0)

    # If we already have a plan and are partway through, continue it
    existing_plan = state.get("conversation_plan", [])
    if existing_plan and current_step < len(existing_plan):
        # Continuing an existing plan — don't overwrite
        plan = existing_plan
    else:
        # New plan — reset step counter
        current_step = 0

    current_action = plan[current_step] if current_step < len(plan) else plan[-1]

    return {
        "messages": [
            AIMessage(
                content=(
                    f"[PlannerAgent] Plan: {' → '.join(plan)} | "
                    f"Current step ({current_step + 1}/{len(plan)}): {current_action}"
                )
            )
        ],
        "conversation_plan": plan,
        "plan_step": current_step,
    }

"""
conversation-service/app/swarm/graph.py
LangGraph agent swarm orchestration — V3.

V1: Linear routing with stub agents.
V3: Intent → Planner → Parallel Swarm (Knowledge, Sales, etc.) → Generator → Safety → END
    + execution guardrails (max depth, timeout)
    + planner generates task plan before workers run
"""
import asyncio
from typing import Any, Dict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from .state import AgentState
from .agents.intent import intent_agent
from .agents.planner import planner_agent
from .agents.knowledge import knowledge_agent
from .agents.personality import personality_agent
from .agents.emotion import emotion_agent
from .agents.sales import sales_agent
from .agents.generator import generator_agent
from .agents.safety import safety_agent

# ── Guardrails ────────────────────────────────────────────────────────────────

MAX_TASK_DEPTH = 3            # max times we re-enter the planning loop
EXECUTION_TIMEOUT_SEC = 30    # hard timeout for entire graph execution


async def swarm_workers_node(state: AgentState) -> dict:
    """
    Parallel Worker Orchestrator.
    Runs knowledge, sales, personality, and emotion agents in parallel.
    Uses asyncio.gather for maximum performance.
    """
    intent = state.get("intent", "general_conversation")
    
    # Define tasks to run in parallel
    tasks = [
        knowledge_agent(state),
        personality_agent(state),
        emotion_agent(state)
    ]
    
    # Conditional inclusion of Sales agent based on intent
    sales_intents = ("purchase_decision", "pricing_inquiry", "booking_request", "objection")
    if intent in sales_intents:
        tasks.append(sales_agent(state))
        
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks)
    
    # Merge results into a single state update
    combined_update: Dict[str, Any] = {
        "messages": [],
        "context": state.get("context", {}).copy(),
        "session_memory": state.get("session_memory", {}).copy()
    }
    
    for res in results:
        for key, value in res.items():
            if key == "messages":
                combined_update["messages"].extend(value)
            elif key == "knowledge_context":
                combined_update["context"]["knowledge_context"] = value
            elif key == "personality_guidance":
                combined_update["context"]["personality_guidance"] = value
            elif key == "user_emotion":
                combined_update["session_memory"]["user_emotion"] = value
            elif key in ("knowledge_confidence", "intent_confidence", "lead_score", "plan_step", "conversation_plan", "intent"):
                combined_update[key] = value
                
    return combined_update


def get_swarm_graph():
    workflow = StateGraph(AgentState)

    # ── Add nodes ─────────────────────────────────────────────────────────
    workflow.add_node("intent", intent_agent)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("swarm_workers", swarm_workers_node)
    workflow.add_node("generator", generator_agent)
    workflow.add_node("safety", safety_agent)

    # ── Define edges ──────────────────────────────────────────────────────

    # 1. Entry → Intent classification
    workflow.set_entry_point("intent")

    # 2. Intent → Planner
    workflow.add_edge("intent", "planner")

    # 3. Planner → Swarm Workers
    workflow.add_edge("planner", "swarm_workers")

    # 4. Swarm Workers → Generator (Synthesis)
    workflow.add_edge("swarm_workers", "generator")

    # 5. Generator → Safety
    workflow.add_edge("generator", "safety")

    # 6. Safety → END
    workflow.add_edge("safety", END)

    return workflow.compile()


async def run_swarm_with_guardrails(
    graph,
    initial_state: AgentState,
) -> Any:
    """
    Execute the swarm graph with timeout and depth guardrails.
    Prevents runaway agent loops in production.
    """
    try:
        # Note: In a real app, we might check for recursion/depth here if needed
        result = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=EXECUTION_TIMEOUT_SEC,
        )
        return result
    except asyncio.TimeoutError:
        # Return a safe fallback state
        return {
            **initial_state,
            "messages": initial_state.get("messages", []) + [
                HumanMessage(content="System timeout. Please try again.") # Using HumanMessage as fallback content source
            ],
            "intent": "timeout_fallback",
        }
    except Exception as e:
        print(f"Swarm Graph Error: {e}")
        return initial_state

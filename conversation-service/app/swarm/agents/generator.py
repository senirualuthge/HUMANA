"""
conversation-service/app/swarm/agents/generator.py
Generator Agent: The 'Voice' of the Digital Human.
Synthesizes all context into a final response.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ..state import AgentState

async def generator_agent(state: AgentState) -> dict:
    """
    Generator Agent: Synthesizes knowledge, personality, and emotion into the final text.
    """
    # Use GPT-4o for high-quality synthesis
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    # Extract context from state
    personality = state.get("context", {}).get("personality_guidance", "You are a professional business assistant.")
    knowledge = state.get("context", {}).get("knowledge_context", "No specific knowledge provided.")
    emotion = state.get("session_memory", {}).get("user_emotion", "neutral")
    intent = state.get("intent", "general_conversation")
    lead_score = state.get("lead_score", 0.0)
    
    # Get the latest CTA from Sales Agent if available
    # We look for the last AIMessage from SalesAgent in the state
    sales_cta = ""
    for msg in reversed(state.get("messages", [])):
        if "[SalesAgent]" in msg.content:
            sales_cta = msg.content.split("CTA: ")[-1] if "CTA: " in msg.content else ""
            break

    system_prompt = (
        f"Role: Digital Human Avatar\n"
        f"Personality Guidelines: {personality}\n"
        f"User Emotion Detected: {emotion}. Reflect this in your tone.\n"
        f"Business/Product Knowledge: {knowledge}\n"
        f"Intent: {intent}\n"
        f"Sales CTA to include (if natural): {sales_cta}\n\n"
        "Goal: Generate a concise, natural-sounding response (1-3 sentences). "
        "Do NOT mention you are an AI or include debug labels like [GeneratorAgent]."
    )
    
    # Get the actual user conversation history (filtering out our debug messages)
    clean_history = [
        m for m in state["messages"] 
        if not (isinstance(m, AIMessage) and any(tag in getattr(m, "content", "") for tag in ["[Intent", "[Planner", "[Knowledge", "[Sales", "[Personality", "[Emotion"]))
    ]
    
    # Call LLM
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        *clean_history
    ])
    
    # We return the NEW message. The state will combine it.
    return {"messages": [response]}

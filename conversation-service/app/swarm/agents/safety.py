from langchain_core.messages import AIMessage
from app.swarm.state import AgentState

async def safety_agent(state: AgentState):
    """
    Checks the generated response for safety, PII leaks, or harsh hallucinations.
    If unsafe, replaces the response with a safe fallback.
    """
    messages = list(state.get("messages", []))
    if not messages:
        return {}
        
    last_msg = messages[-1]
    
    # We only check AI messages
    if last_msg.type != "ai":
        return {}
        
    content = last_msg.content.lower()
    
    # Very basic substring matching for typical forbidden terms or patterns
    # In a production system, this could be a call to Azure Content Safety, 
    # OpenAI moderation API, or a dedicated NLP model.
    unsafe_keywords = [
        "social security number", "credit card", "password is",
        "hack", "bypass", "exploit", "ignore previous instructions"
    ]
    
    for kw in unsafe_keywords:
        if kw in content:
            # Mask or replace unsafe message
            safe_msg = AIMessage(content="I'm sorry, I cannot discuss or provide that sensitive information.")
            # Overwrite the last message by returning it
            return {"messages": [safe_msg]}
            
    return {}

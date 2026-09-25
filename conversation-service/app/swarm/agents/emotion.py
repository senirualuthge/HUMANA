import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.swarm.state import AgentState

async def emotion_agent(state: AgentState):
    """
    Analyzes the digital human's planned response to determine
    the optimal emotional state for the 3D avatar.
    """
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    
    messages = list(state.get("messages", []))
    if not messages:
        return {"emotion_data": {"emotion": "neutral", "intensity": 0.5}}
        
    latest_message = messages[-1].content
    
    system_prompt = """You are an emotion classification engine.
Analyze the user's latest message and classify their emotional state.
Return ONLY ONE of these exact words: happy, sad, angry, frustrated, confused, neutral, excited"""

    prompt = f"User's message: {latest_message}"
    
    try:
        response = await model.ainvoke([
            SystemMessage(content=system_prompt), 
            HumanMessage(content=prompt)
        ])
        
        user_emotion = response.content.strip().lower()
        return {"user_emotion": user_emotion}
    except Exception as e:
        print(f"Emotion classification error: {e}")
        return {"user_emotion": "neutral"}

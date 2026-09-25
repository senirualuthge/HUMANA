from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from app.swarm.state import AgentState

async def personality_agent(state: AgentState):
    """
    Takes the generated context, intent, and previous messages
    and formulates a response matching the brand voice.
    """
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    messages = list(state.get("messages", []))
    
    # Extract brand voice from context if available
    context = state.get("context", {})
    brand_voice = context.get("brand_voice", "helpful, professional, and friendly")
    
    knowledge_context = state.get("knowledge_context", "")
    
    system_prompt = f"You are a personality analysis engine for a digital human representative.\n"
    if brand_voice:
        system_prompt += f"The brand voice is: {brand_voice}.\n"
        
    system_prompt += "\nBased on the user's message, provide brief guidance on how the avatar should respond to perfectly align with the brand voice and the user's current situation."
    
    new_messages = [SystemMessage(content=system_prompt)] + messages
    
    response = await model.ainvoke(new_messages)
    
    return {"personality_guidance": response.content}

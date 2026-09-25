"""
conversation-service/tests/test_swarm_v3.py
End-to-end verification of the V3 Swarm architecture.
"""
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

os.environ["OPENAI_API_KEY"] = "sk-mock-key"

# Add app directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import HumanMessage
from app.swarm.graph import get_swarm_graph
from app.swarm.state import AgentState

import pytest

@pytest.mark.asyncio
async def test_end_to_end_purchase_intent():
    print("\n--- Testing Purchase Intent ---")
    initial_state = {
        "messages": [HumanMessage(content="I'm interested in the Business plan. What features are included and can I book a demo?")],
        "context": {"business_id": "test_corp_123"},
        "session_memory": {},
    }
    
    # Mocking external calls to avoid needing actual API keys/DB for basic logic test
    from unittest.mock import AsyncMock
    with patch("app.swarm.graph.intent_agent", new_callable=AsyncMock) as mock_intent, \
         patch("app.swarm.graph.knowledge_agent", new_callable=AsyncMock) as mock_kb, \
         patch("app.swarm.graph.generator_agent", new_callable=AsyncMock) as mock_gen, \
         patch("app.swarm.graph.planner_agent", new_callable=AsyncMock) as mock_plan, \
         patch("app.swarm.graph.sales_agent", new_callable=AsyncMock) as mock_sales, \
         patch("app.swarm.graph.personality_agent", new_callable=AsyncMock) as mock_pers, \
         patch("app.swarm.graph.emotion_agent", new_callable=AsyncMock) as mock_emot, \
         patch("app.swarm.graph.safety_agent", new_callable=AsyncMock) as mock_safety:
        
        # Build the graph inside the mock context so the state graph uses the mocked callables
        graph = get_swarm_graph()
        
        # 1. Mock Intent Agent
        from langchain_core.messages import AIMessage
        mock_intent.return_value = {
            "intent": "purchase_decision",
            "intent_confidence": 0.95,
            "messages": [AIMessage(content="[IntentAgent] Classified: purchase_decision (conf=0.95)")]
        }
        
        # 2. Mock Planner Agent
        mock_plan.return_value = {
            "conversation_plan": "Acknowledge interest -> Explain features -> Propose demo",
            "messages": [AIMessage(content="[PlannerAgent] Plan: Acknowledge interest -> Explain features -> Propose demo")]
        }

        # 3. Mock Knowledge / Sales / Personality / Emotion
        mock_kb.return_value = {"knowledge_context": "Business Plan includes 24/7 Support and Advanced Analytics."}
        mock_sales.return_value = {"lead_score": 0.8}
        mock_pers.return_value = {"personality_context": "Professional"}
        mock_emot.return_value = {"emotion_context": "Enthusiastic"}

        # 4. Mock Generator
        mock_gen.return_value = {
            "messages": [AIMessage(content="The Business plan features 24/7 support and advanced analytics. I'd be happy to set up a personalized demo for you right now—what time works best?")]
        }
        
        # 5. Mock Safety
        mock_safety.return_value = {
            "messages": [AIMessage(content="[SafetyAgent] Message is SAFE")]
        }

        result = await graph.ainvoke(initial_state)
        
        print(f"Final Intent: {result['intent']}")
        print(f"Lead Score: {result['lead_score']}")
        print(f"Plan: {result['conversation_plan']}")
        print(f"Generated Message: {result['messages'][-2].content}")
        print(f"Safety Output: {result['messages'][-1].content}")
        
        assert result["intent"] == "purchase_decision"
        assert result["lead_score"] > 0.4
        assert "demo" in result["messages"][-2].content.lower()
        assert "safe" in result["messages"][-1].content.lower()
        print("Test passed!")

async def main():
    await test_end_to_end_purchase_intent()

if __name__ == "__main__":
    asyncio.run(main())

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage
from app.swarm.agents.knowledge import knowledge_agent
from app.swarm.state import AgentState

@pytest.mark.asyncio
async def test_knowledge_agent_no_business_id():
    state: AgentState = {
        "messages": [HumanMessage(content="What are your hours?")],
        "context": {},
        "knowledge_context": "",
        "knowledge_confidence": 0.0,
        "intent": "",
        "intent_confidence": 0.0,
        "lead_score": 0.0,
        "conversation_plan": [],
        "plan_step": 0,
        "session_memory": {},
        "long_term_context": ""
    }
    
    result = await knowledge_agent(state)
    assert "Warning: No business_id provided" in result["messages"][0].content
    assert result["knowledge_confidence"] == 0.0

@pytest.mark.asyncio
async def test_knowledge_agent_empty_messages():
    state: AgentState = {
        "messages": [],
        "context": {"business_id": "test_123"},
        "knowledge_context": "",
        "knowledge_confidence": 0.0,
        "intent": "",
        "intent_confidence": 0.0,
        "lead_score": 0.0,
        "conversation_plan": [],
        "plan_step": 0,
        "session_memory": {},
        "long_term_context": ""
    }
    
    result = await knowledge_agent(state)
    assert "No user message found" in result["messages"][0].content

@pytest.mark.asyncio
@patch("app.swarm.agents.knowledge.PGVector")
async def test_knowledge_agent_success(mock_pgvector):
    mock_instance = MagicMock()
    doc1 = MagicMock()
    doc1.page_content = "Store hours are 9 AM to 5 PM."
    doc2 = MagicMock()
    doc2.page_content = "We are located at 123 Main St."
    
    mock_instance.asimilarity_search = AsyncMock(return_value=[doc1, doc2])
    mock_pgvector.return_value = mock_instance
    
    state: AgentState = {
        "messages": [HumanMessage(content="What are your hours?")],
        "context": {"business_id": "test_123"},
        "knowledge_context": "",
        "knowledge_confidence": 0.0,
        "intent": "",
        "intent_confidence": 0.0,
        "lead_score": 0.0,
        "conversation_plan": [],
        "plan_step": 0,
        "session_memory": {},
        "long_term_context": ""
    }
    
    result = await knowledge_agent(state)
    
    assert result["knowledge_confidence"] == 0.8
    assert "Store hours are 9 AM to 5 PM." in result["knowledge_context"]
    assert "123 Main St." in result["knowledge_context"]
    assert "Retrieved 2 relevant knowledge snippets." in result["messages"][0].content
    mock_instance.asimilarity_search.assert_called_once_with("What are your hours?", k=3)

@pytest.mark.asyncio
@patch("app.swarm.agents.knowledge.PGVector")
async def test_knowledge_agent_no_results(mock_pgvector):
    mock_instance = MagicMock()
    mock_instance.asimilarity_search = AsyncMock(return_value=[])
    mock_pgvector.return_value = mock_instance
    
    state: AgentState = {
        "messages": [HumanMessage(content="Do you sell cars?")],
        "context": {"business_id": "test_123"},
        "knowledge_context": "",
        "knowledge_confidence": 0.0,
        "intent": "",
        "intent_confidence": 0.0,
        "lead_score": 0.0,
        "conversation_plan": [],
        "plan_step": 0,
        "session_memory": {},
        "long_term_context": ""
    }
    
    result = await knowledge_agent(state)
    
    assert result["knowledge_confidence"] == 0.0
    assert result["knowledge_context"] == "No relevant information found in the knowledge base."
    assert "No relevant knowledge found for this query." in result["messages"][0].content

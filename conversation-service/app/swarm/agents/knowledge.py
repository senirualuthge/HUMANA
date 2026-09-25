import os
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.messages import AIMessage
from app.swarm.state import AgentState

# Configuration
# DATABASE_URL should be set in environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://humana:password@db:5432/humana_v2")

async def knowledge_agent(state: AgentState) -> dict:
    """
    RAG Agent: Retrieves relevant business context from PGVector.
    """
    # Get the last message from the user
    user_messages = [m for m in state["messages"] if m.type == "human"]
    if not user_messages:
        return {"messages": [AIMessage(content="No user message found to query knowledge base.")]}
    
    query = user_messages[-1].content
    business_id = state["context"].get("business_id")
    
    if not business_id:
        return {
            "knowledge_context": "No business context available.",
            "knowledge_confidence": 0.0,
            "messages": [AIMessage(content="Warning: No business_id provided. Skipping knowledge retrieval.")]
        }

    try:
        # Initialize Vector Store
        # langchain-postgres PGVector uses a connection string
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name=f"business_{business_id}",
            connection=DATABASE_URL,
            use_jsonb=True,
        )
        
        # Retrieve top 3 relevant chunks
        docs = await vectorstore.asimilarity_search(query, k=3)
        
        if not docs:
            return {
                "knowledge_context": "No relevant information found in the knowledge base.",
                "knowledge_confidence": 0.0,
                "messages": [AIMessage(content="No relevant knowledge found for this query.")]
            }

        context_text = "\n---\n".join([doc.page_content for doc in docs])
        
        # Success: Update state with context and confidence
        return {
            "knowledge_context": context_text,
            "knowledge_confidence": 0.8,
            "messages": [AIMessage(content=f"Retrieved {len(docs)} relevant knowledge snippets.")]
        }

    except Exception as e:
        print(f"Error in knowledge_agent: {e}")
        return {
            "knowledge_context": f"Error retrieving knowledge: {str(e)}",
            "knowledge_confidence": 0.0,
            "messages": [AIMessage(content="An error occurred while accessing the knowledge base.")]
        }

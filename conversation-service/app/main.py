from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.swarm.graph import get_swarm_graph
from langchain_core.messages import HumanMessage
import json

app = FastAPI(title="Humana V2 Conversation Service")

swarm_graph = get_swarm_graph()

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
async def health():
    return {"status": "ok", "component": "conversation-service"}

@app.websocket("/ws/swarm")
async def websocket_swarm(websocket: WebSocket):
    await websocket.accept()
    print("New connection to Conversation Service Swarm")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received in swarm: {data}")
            
            # Simple invocation of LangGraph for demo purposes
            inputs = {
                "messages": [HumanMessage(content=data)],
                "context": {},
                "current_agent": "intent_agent"
            }
            async for output in swarm_graph.astream(inputs):
                for key, value in output.items():
                    if "messages" in value and len(value["messages"]) > 0:
                        last_message = value["messages"][-1].content
                        await websocket.send_text(json.dumps({
                            "agent": key,
                            "message": last_message
                        }))
    except WebSocketDisconnect:
        print("Swarm WS Disconnected")
    except Exception as e:
        print(f"Swarm WS Error: {e}")

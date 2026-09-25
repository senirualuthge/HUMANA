from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import websockets
import os

app = FastAPI(title="Humana V2 API Gateway")

CONVERSATION_SERVICE_WS = os.getenv("CONVERSATION_SERVICE_WS", "ws://conversation-service:8000")

@app.get("/health")
async def health():
    return {"status": "ok", "component": "gateway"}

async def forward_ws(source, destination):
    try:
        while True:
            if isinstance(source, WebSocket):
                data = await source.receive_text()
                await destination.send(data)
            else:
                data = await source.recv()
                await destination.send_text(data)
    except Exception as e:
        pass

@app.websocket("/ws/chat")
async def websocket_proxy(websocket: WebSocket):
    await websocket.accept()
    try:
        async with websockets.connect(f"{CONVERSATION_SERVICE_WS}/ws/swarm") as backend_ws:
            task1 = asyncio.create_task(forward_ws(websocket, backend_ws))
            task2 = asyncio.create_task(forward_ws(backend_ws, websocket))
            
            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
    except Exception as e:
        print(f"Connection failed: {e}")
        await websocket.close()

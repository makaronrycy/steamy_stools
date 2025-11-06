# server_http.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
from typing import List, Optional, Any, Dict
import json

from fastmcp import Client  

def to_jsonable(obj: Any) -> Any:
    """Upewnia się, że wynik jest JSON-owalny."""
    payload = getattr(obj, "data", obj)
    try:
        json.dumps(payload)
        return payload
    except TypeError:
        return jsonable_encoder(payload)

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = Client("server_mcp.py")
    await client.__aenter__()
    await client.ping()
    app.state.mcp_client = client
    yield
    await client.__aexit__(None, None, None)

app = FastAPI(title="Hot Seat Game API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.get("/")
async def root():
    return {
        "name": "Hot Seat Game API",
        "version": "2.0 (FastMCP client)",
        "endpoints": {"websocket": "/ws", "tools": "/api/tools/{tool_name}", "health": "/health"},
    }

@app.get("/health")
async def health():
    return {"status": "ok", "mcp": True}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data: Dict[str, Any] = await websocket.receive_json()
            tool_name = data.get("tool")
            arguments = data.get("arguments") or {}

            try:
                result_obj = await app.state.mcp_client.call_tool(tool_name, arguments)
                payload = to_jsonable(result_obj)
                response = {"type": "tool_response", "tool": tool_name, "data": {"result": payload}}
            except Exception as e:
                response = {"type": "tool_response", "tool": tool_name, "data": {"error": str(e)}}

            await websocket.send_json(response)
            await manager.broadcast({"type": "update", "message": f"Wywołano narzędzie: {tool_name}"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    try:
        result_obj = await app.state.mcp_client.call_tool(tool_name, arguments)
        return {"result": to_jsonable(result_obj)}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Uruchamianie serwera HTTP/WebSocket na porcie 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

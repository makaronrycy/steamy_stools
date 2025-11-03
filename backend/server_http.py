# server_http.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
from typing import List, Optional, Any, Dict
import os

from fastmcp import Client  # klient FastMCP
from openai import OpenAI

def to_jsonable(obj: Any) -> Any:
    """Zapewnia JSON-owalność wyniku MCP (CallToolResult .data)."""
    payload = getattr(obj, "data", obj)
    try:
        # szybki test serializacji
        jsonable_encoder(payload)
        return payload
    except Exception:
        return jsonable_encoder(payload)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # MCP client uruchamia server_mcp.py jako subprocess (STDIO)
    client = Client("server_mcp.py")
    await client.__aenter__()
    await client.ping()
    app.state.mcp_client = client

    # OpenAI (LLM) — klucz z ENV
    app.state.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    yield

    await client.__aexit__(None, None, None)

app = FastAPI(title="Hot Seat Game API", lifespan=lifespan)

# CORS: w dev pozwól na frontend pod localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # dostosuj w prod
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
        "endpoints": {"websocket": "/ws", "tools": "/api/tools/{tool_name}", "health": "/health", "llm": "/api/llm"},
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
                result_obj = await app.state.mcp_client.call_tool(tool_name, arguments)  # type: ignore
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
        result_obj = await app.state.mcp_client.call_tool(tool_name, arguments)  # type: ignore
        return {"result": to_jsonable(result_obj)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/llm")
async def chat_with_llm(request: Dict[str, Any]):
    """Proxy do LLM (OpenAI) — klucz po stronie serwera, front nie widzi SECRETów."""
    try:
        message = request.get("message", "")
        response = app.state.openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś pomocnym asystentem w grze 'Gorące krzesła'."},
                {"role": "user", "content": message}
            ],
            max_tokens=512,
            temperature=0.7
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Uruchamianie serwera HTTP/WebSocket na porcie 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

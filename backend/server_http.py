# server_http.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
from typing import List, Optional, Any, Dict
import os
import subprocess
import httpx
from openai import OpenAI
from pathlib import Path
from dotenv import dotenv_values

# Import GitHub analysis function
# Import GitHub analysis function
from code_metrics import full_github_review
# Import Assumptions dirs function
from assumptions_dirs import create_assumption_dirs
from objectives import analyze_assumptions

# URL do agent-client (wewnętrzna sieć Docker)
AGENT_CLIENT_URL = os.getenv("AGENT_CLIENT_URL", "http://agent-client:3000")
AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://agent-server:10000")

def to_jsonable(obj: Any) -> Any:
    """Zapewnia JSON-owalność wyniku."""
    payload = getattr(obj, "data", obj)
    try:
        jsonable_encoder(payload)
        return payload
    except Exception:
        return jsonable_encoder(payload)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # OpenAI (LLM) — klucz z ENV
    app.state.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    yield

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
        "endpoints": {
            "websocket": "/ws", 
            "tools": "/api/tools/{tool_name}", 
            "health": "/health", 
            "llm": "/api/llm",
            "github_analyze": "/api/github/analyze"
        },
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
            msg_type = data.get("type", "unknown")
            
            # WebSocket służy głównie do broadcastów i statusów
            # Tool calls idą przez agent-client (/start_agent na porcie 3000)
            response = {
                "type": "ack", 
                "message": f"Received message type: {msg_type}",
                "data": data
            }
            
            await websocket.send_json(response)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, arguments: Dict[str, Any]):
    """
    Deprecated: Tool calls now go through agent-client on port 3000.
    Use POST /start_agent on agent-client instead.
    """
    return {
        "error": "deprecated",
        "message": "Tool calls now go through agent-client. Use POST http://localhost:3000/start_agent instead."
    }

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

# === Agent Client Proxy (CORS bypass) ===
@app.post("/api/agent/start")
async def proxy_start_agent(request: Dict[str, Any]):
    """
    Proxy endpoint dla agent-client.
    Frontend wywołuje ten endpoint, a backend przekazuje request do agent-client.
    Rozwiązuje problem CORS (Sanic nie obsługuje CORS domyślnie).
    """
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{AGENT_CLIENT_URL}/start_agent",
                json=request,
                headers={"Content-Type": "application/json"}
            )
            return response.json()
    except httpx.TimeoutException:
        return {"error": "timeout", "message": "Przekroczono czas oczekiwania na odpowiedź agenta."}
    except Exception as e:
        return {"error": str(e), "message": "Nie udało się połączyć z agent-client."}

@app.get("/api/agent/people")
async def proxy_list_people():
    """
    Pobiera listę osób z agent-server.
    Proxy dla endpointu GET /list_people na porcie 10000.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{AGENT_SERVER_URL}/list_people")
            return response.json()
    except httpx.TimeoutException:
        return {"error": "timeout", "message": "Upłynął czas oczekiwania na listę osób."}
    except Exception as e:
        return {"error": str(e), "message": "Nie można pobrać listy osób z agent-server."}

@app.post("/api/github/analyze")
async def analyze_github(background_tasks: BackgroundTasks):
    """
    Uruchamia analizę repozytorium GitHub.
    Wykonuje się w tle, aby nie blokować requestu.
    """
    try:
        # Opcja 1: Uruchom w tle (zalecane dla długich operacji)
        background_tasks.add_task(full_github_review)
        return {
            "status": "started",
            "message": "Analiza GitHub została uruchomiona w tle. Wyniki zostaną zapisane do MongoDB."
        }
        
        # Opcja 2: Uruchom synchronicznie (dla testów lub krótkich analiz)
        # full_github_review()
        # return {
        #     "status": "completed",
        #     "message": "Analiza GitHub została zakończona. Wyniki zapisane w MongoDB."
        # }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Błąd podczas analizy: {str(e)}"
        }

@app.get("/api/github/status")
async def github_analysis_status():
    """
    Sprawdza status analizy GitHub (opcjonalnie - możesz dodać tracking stanu).
    """
    return {
        "status": "not_implemented",
        "message": "Endpoint do sprawdzania statusu - do zaimplementowania z użyciem Redis/database."
    }

@app.post("/api/neo4j/init")
async def init_neo4j_database():
    """
    Inicjalizuje bazę danych Neo4j uruchamiając skrypt w kontenerze steamy-agent-server.
    """
    try:
        # 1. Uruchom skrypt z odpowiednim URI
        # docker exec -e NEO4J_URI=neo4j+s://<HOST> -e NEO4J_USERNAME=neo4j -e NEO4J_PASSWORD=<PASSWORD> steamy-agent-server python -m src.neo4j_retriever.__init__
        env_path = Path(__file__).resolve().parents[1] / "agent_server" / ".env"
        env_values = dotenv_values(env_path) if env_path.exists() else {}
        neo4j_uri = env_values.get("NEO4J_URI") or os.getenv("NEO4J_URI")
        neo4j_username = env_values.get("NEO4J_USERNAME") or os.getenv("NEO4J_USERNAME")
        neo4j_password = env_values.get("NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD")

        if not all([neo4j_uri, neo4j_username, neo4j_password]):
            return {
                "status": "error",
                "message": "Brakuje NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD w agent_server/.env lub w ENV backendu."
            }

        cmd = [
            "docker", "exec", 
            "-e", f"NEO4J_URI={neo4j_uri}",
            "-e", f"NEO4J_USERNAME={neo4j_username}",
            "-e", f"NEO4J_PASSWORD={neo4j_password}",
            "steamy-agent-server", 
            "python", "-m", "src.neo4j_retriever.__init__"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Baza danych zainicjalizowana pomyślnie. (URI: {neo4j_uri})\nLogi:\n{result.stdout}"
            }
        else:
            return {
                "status": "error",
                "message": f"Błąd inicjalizacji bazy (URI: {neo4j_uri}):\n{result.stderr}"
            }
            

    except Exception as e:
        return {
            "status": "error",
            "message": f"Wystąpił wyjątek podczas inicjalizacji DB: {str(e)}"
        }

@app.post("/api/assumptions/init")
async def init_assumptions_dirs():
    """
    Tworzy katalogi na założenia projektowe (assumptions).
    """
    try:
        result = create_assumption_dirs()
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Błąd endpointu assumptions: {str(e)}"
        }

@app.post("/api/assumptions/analyze")
async def run_assumptions_analysis(background_tasks: BackgroundTasks):
    """
    Uruchamia analizę założeń (objectives.py) w tle.
    Analizuje pliki w assumptions/[projekt]/start_assumptions.
    """
    try:
        # For long running tasks, use background logic or just run sync if it's fast enough
        # Given it calls OpenAI multiple times, sync might time out. 
        # But for simplicity let's try sync first, or wrap in background task and return status.
        # User requested "click button -> run analysis". 
        
        result = analyze_assumptions()
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": f"Błąd analizy założeń: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Uruchamianie serwera HTTP/WebSocket na porcie 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

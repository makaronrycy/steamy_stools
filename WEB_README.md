# Gorące Krzesła - Prototyp Architektury MCP

##  Przegląd projektu



**Status: Wersja demonstracyjna**  
Kod stanowi proof-of-concept (PoC) i ilustruje docelową architekturę systemu. Wszystkie komponenty zostaną rozwinięte zgodnie z pełną specyfikacją projektu.

---

##  Architektura systemu

### Przegląd komponentów

```
┌─────────────────────┐    WebSocket/HTTP    ┌─────────────────────┐    MCP (STDIO)    ┌─────────────────────┐
│                     │◄────────────────────►│                     │◄─────────────────►│                     │
│   GUI Application   │                      │   HTTP/WS Gateway   │                   │    MCP Server       │
│  (host_desktop_*)   │                      │  (server_http.py)   │                   │  (server_mcp.py)    │
│                     │                      │                     │                   │                     │
└─────────────────────┘                      └─────────────────────┘                   └─────────────────────┘
         │                                              │                                          │
         │                                              │                                          │
         ▼                                              ▼                                          ▼
   ┌─────────────┐                                ┌─────────────┐                           ┌─────────────┐
   │    LLM      │                                │  FastAPI    │                           │   FastMCP   │
   │  (OpenAI)   │                                │   + WS      │                           │   Tools     │
   └─────────────┘                                └─────────────┘                           └─────────────┘
```

### Warstwa 1: GUI Application (Frontend)
- **Plik:** `host_desktop.py`
- **Technologia:** CustomTkinter + WebSocket Client + OpenAI API
- **Funkcje:**
  - Interfejs użytkownika gry
  - Komunikacja z LLM (OpenAI GPT)
  - Real-time komunikacja z gateway przez WebSocket
  - Obsługa narzędzi MCP (pytania, ranking, etc.)

### Warstwa 2: HTTP/WebSocket Gateway (Middleware)
- **Plik:** `server_http.py`
- **Technologia:** FastAPI + WebSocket + FastMCP Client
- **Funkcje:**
  - Proxy między GUI a MCP Server
  - WebSocket server dla real-time komunikacji
  - HTTP API dla alternatywnej komunikacji
  - Zarządzanie cyklem życia MCP subprocess
  - Serializacja danych MCP do JSON

### Warstwa 3: MCP Server (Backend)
- **Plik:** `server_mcp.py`
- **Technologia:** FastMCP + STDIO Transport
- **Funkcje:**
  - Logika „Gorące Krzesła"
  - Narzędzia MCP (tools): pytania, gracze, wyniki
  - Zasoby MCP (resources): stan gorących krzeseł
  - Zarządzanie stanem gry w pamięci

---


##  Instalacja i uruchomienie

### Wymagania
- Python 3.9+
- Klucz API OpenAI

### Szybki start
```bash
# 1. Klonuj repository
git clone <repository-url>
cd gorace-krzesla

# 2. Zainstaluj zależności
pip install fastapi uvicorn[standard] fastmcp customtkinter websockets openai

# 3. Ustaw klucz OpenAI

set OPENAI_API_KEY=sk-...       # Windows CMD


# 4. Uruchom gateway (Terminal 1)
python server_http.py

# 5. Uruchom aplikację (Terminal 2)  
python host_desktop.py

# 6. W GUI kliknij "Połącz WS"
```

---

##  Obecne możliwości (Proof of Concept)

###  Zaimplementowane
- [x] Architektura 3-warstwowa (GUI ↔ Gateway ↔ MCP)
- [x] Komunikacja WebSocket w czasie rzeczywistym
- [x] Integracja z OpenAI GPT
- [x] Podstawowe narzędzia MCP (pytania, ranking)
- [x] Transport MCP przez STDIO
- [x] Zarządzanie subprocess MCP przez gateway
- [x] JSON serializacja wyników MCP

###  W planach (Docelowa wersja)
- [ ] Pełna baza pytań z kategoriami
- [ ] System sesji i wielu graczy
- [ ] Autoryzacja i bezpieczeństwo
- [ ] Persystencja danych (baza danych)
- [ ] UI/UX dla gry wieloosobowej
- [ ] Zaawansowane narzędzia MCP
- [ ] Monitoring i logging
- [ ] Deployment w chmurze
- [ ] Konfiguracja i zarządzanie

---



### Skalowalność
```
Frontend Layer:
├── Web UI (React/Vue)
├── Desktop App (Electron/Python)
├── Mobile App (React Native)
└── API Clients

Gateway Layer:
├── Load Balancer
├── API Gateway (FastAPI/Express)
├── WebSocket Manager
├── Session Management
└── Authentication

Backend Layer:
├── MCP Servers (FastMCP/Node)
├── Game Logic Services
├── Database Layer (PostgreSQL/Redis)
├── LLM Integration (OpenAI/Anthropic)
└── File Storage (S3/MinIO)
```

### Technologie docelowe
- **Frontend:** React/Vue.js, Electron, React Native
- **Backend:** FastAPI, Node.js, PostgreSQL, Redis
- **MCP:** FastMCP, oficjalne SDK
- **LLM:** OpenAI, Anthropic, lokalne modele
- **Infrastruktura:** Docker, Kubernetes, AWS/GCP
- **Monitoring:** Prometheus, Grafana, ELK Stack

---




##  Disclaimer

**Ten kod jest wersją koncepcyjną i demonstracyjną.** Realizuje początkowy model architektury MCP oraz komunikacji między komponentami. Pełna funkcjonalność, bezpieczeństwo, skalowalność i optymalizacje zostaną zaimplementowane w kolejnych fazach rozwoju zgodnie ze specyfikacją projektu.
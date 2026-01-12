# Steamy Stools 

## Wymagania

- **Docker Desktop** (z Docker Compose)
- **Git**

---

## Szybki start

### 1. Sklonuj repozytorium

```bash
git clone <URL_REPO>
cd steamy_stools
```

### 2. Skonfiguruj zmienne środowiskowe

Skopiuj przykładowy plik konfiguracyjny:

```bash
cp .env.example .env
```

Edytuj plik `.env` i uzupełnij wymagane wartości:

```env
# === WYMAGANE ===

# Token GitHub (wygeneruj na https://github.com/settings/tokens)
# Wymagane uprawnienia: repo, read:org
GITHUB_TOKEN=ghp_twoj_token

# Klucz API OpenAI (dla funkcji agenta AI)
OPENAI_API_KEY=sk-twoj_klucz

# === OPCJONALNE ===

# Domyślne repozytorium do analizy
GITHUB_URL=https://github.com/owner/repo
OWNER=owner
REPO_NAME=repo
MAIN_BRANCH=main

# Parametry analizy
PROJECT_START_TIME=2023-01-01
WEEKS=10
```

### Pliki .env w podfolderach

Przy uruchomieniu przez **Docker** (zalecane) - wystarczy tylko główny plik `.env`.

Jeśli uruchamiasz komponenty **lokalnie bez Dockera**, musisz również skonfigurować:

#### agent_server/.env
```env
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=twoje_haslo
OPENAI_API_KEY=sk-twoj_klucz
```

#### agent_client/.env
```env
MCP_SERVER_URL=http://localhost:10000
OPENAI_API_KEY=sk-twoj_klucz

# Opcjonalne - Langfuse (monitoring AI)
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

#### backend/.env
```env
GITHUB_URL=https://github.com/owner/repo
GITHUB_TOKEN=ghp_twoj_token
OWNER=owner
REPO_NAME=repo
MAIN_BRANCH=main

SONAR_HOST_URL=http://localhost:9000
SONAR_TOKEN=squ_twoj_token
SONAR_PROJECT_KEY=project_key
SONAR_PROJECT_NAME=ProjectName
SONAR_API_URL=http://localhost:9000
MONGO_URI=mongodb://localhost:27017

WEEKS=10
PROJECT_START_TIME=2023-01-01
```

### 3. Uruchom aplikację

```bash
docker-compose up -d --build
```

Pierwsze uruchomienie może potrwać kilka minut (pobieranie obrazów i budowanie kontenerów).

### 4. Sprawdź status

```bash
docker ps --filter "name=steamy"
```

Wszystkie kontenery powinny mieć status `Up` lub `healthy`.

---

##  Dostęp do usług

| Usługa | URL | Opis |
|--------|-----|------|
| **Frontend** | http://localhost:5173 | Główny interfejs użytkownika |
| **Panel Admina** | http://localhost:5173/admin | Hasło: `admin123` |
| **Backend API** | http://localhost:8000 | REST API |
| **Agent Client** | http://localhost:3000 | Interfejs agenta AI |
| **SonarQube** | http://localhost:9000 | Analiza jakości kodu |
| **Neo4j Browser** | http://localhost:7474 | Baza grafowa |
| **MongoDB** | mongodb://localhost:27017 | Baza dokumentowa |

---

## Konfiguracja SonarQube (pierwsza konfiguracja)

1. Otwórz http://localhost:9000
2. Zaloguj się: `admin` / `admin`
3. Zmień hasło na nowe
4. Przejdź do **My Account → Security → Generate Token**
5. Skopiuj token i wklej do `.env`:

```env
SONAR_TOKEN=squ_wygenerowany_token
```

6. Zrestartuj backend:

```bash
docker-compose restart backend
```

---

## Struktura projektu

```
steamy_stools/
├── frontend/           # React + TypeScript (Vite)
├── backend/            # Python (FastAPI)
├── agent_server/       # Serwer MCP (AI Agent)
├── agent_client/       # Klient MCP
├── github_review/      # Skrypty analizy GitHub
├── docker-compose.yml  # Konfiguracja Docker
├── .env.example        # Przykładowe zmienne środowiskowe
└── .env                # Twoje zmienne (nie commituj!)
```

---

## Przydatne komendy

```bash
# Uruchom wszystko
docker-compose up -d

# Zatrzymaj wszystko
docker-compose down

# Zobacz logi
docker-compose logs -f

# Logi konkretnego serwisu
docker-compose logs -f backend

# Przebuduj po zmianach
docker-compose up -d --build

# Restart konkretnego serwisu
docker-compose restart backend
```

---

##  Rozwiązywanie problemów

### Kontener się restartuje
```bash
docker logs steamy-<nazwa> --tail 50
```

### Port zajęty
Zmień port w `docker-compose.yml` lub zatrzymaj konfliktujący proces.

### Brak połączenia z bazą
Poczekaj aż kontenery `neo4j` i `mongodb` będą `healthy`:
```bash
docker ps --filter "name=steamy"
```

---

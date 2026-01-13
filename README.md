# Steamy Stools
## Opis programu
Steamy stools to aplikacja mająca za zadanie automatyzacje procesy "Gorących Krzeseł", czyli wywiadów końcowych występujących na końcu przedmiotu ZSD.
Początkowo program ocenia wkład studentów w projektowe repozytoria Github, oraz wyciąga informacje na temat spełnienia założen na podstawie prezentacji początkowej i końcowej.

Po ocenieniu pracy i spełnienia założeń, możliwe jest przeprowadzenie rozmowy z agentem AI, w której agent pyta o oceny siebie, różnych osób, projektów, oraz o wkład na temat własnej przyszłości i feedback o przedmiocie. 

Po zakończeniu rozmowy z wszystkimi osobami, możliwa jest generacja końcowego raportu z wynikami.

## Działanie poszczególnych modułów
- ### [Klient rozmowy](agent_client)
Zadaniem klienta rozmowy jest komunikacja z agentem oraz przypisywanie stanów agenta. Serwis jest postawiony na `Sanic`, pozwalając nam na wiele połączeń naraz.
Cała [logika agenta](agent_client/src/__init__.py) jest uruchamiana poprzez endpoint \start_agent.
Jeśli student pierwszy raz rozpoczyna konwersacje, na bazie danych neo4j tworzy się węzeł `ConversationSession`, który przetrzymuje dane sesji, i.e. aktualny stan(`pending_state`), o co/kogo jest pytanie (`pending_target`) i czy student ukończył rozmowe (`completed`).
Po każdej wiadomości tworzony jest także węzeł `ConversationMessage`, zawierający wiadomość studenta/agenta, oraz dla jakiego pytania była zadana wiadomość.
Powyższe węzły pozwalają nam kontynuować konwersacje nawet przy wyjściu ze strony.
Następujące [stany](agent_client/src/states) to:
- `initial` - Stan inicjalny, pyta użytkownika o potwierdzenie swoich danych
- `self_evaluation` - Pytanie o samoocene własną
- `evaluate_teammate_grade` - Pytanie o ocene członka grupy
- `evaluate_project_grade` -Pytanie o ocene projektów
- `evaluate_leader_grade` - Pytanie o ocene lidera grupy, różni się od oceny członka tym że pytamy o umiejętności zarządzania
- `evaluate_objectives` - Ogólne pytanie o założenia grup, czy zostały spełnione
- `evaluate_assumption` - Pytania o poszczególne założenia wykryte automatycznie
- `masters_intent` - Pytanie czy student zamierza kontynuować magisterkę
- `study_program_feedback` - Pytanie o przedmiot ZSD, jakie zmiany by wprowadził i jego wrażenia
- `done` - Końcowy stan, w którym agent się żegna/przechodzi do chit-chatu
[Plik](agent_client/src/states/__init__.py) definiuje także [narzędzia](agent_server.src/server_resources/tools.py) dostępne dla agenta i nazwy [promptów](agent_server/src/server_resources/prompt.py) na serwerze MCP,gdzie narzędzia są w [filtrowane](agent_client/src/utils.py), przez to że serwer MCP domyślnie zwraca wszystkie.
Rozmowa składa się z dwóch głównych agentów, `QuestionAgent` przyjmującego prompta z pytaniem, oraz `VerificationAgent`, dla których każdy stan ma osobno określonego prompta.
Zadaniem `QuestionAgent` jest zadanie pytania aktualnego stanu, gdzie przekazywane są mu ewentualne informacje celu pytania (o kim/o czym gadamy). Posiada także narzędzie zwracające informacje o studencie z którym rozmawia.
`VerificationAgent` weryfikuje odpowiedź studenta, stwierdzając czy zawiera ocene, wystarczającą ocene, oraz czy student mówi na temat (jeśli student mówi o np. Kasi, a tematem pytaniu jest Kuba, agent nie przyjmuje odpowiedzi). Jeśli agent uzna odpowiedź studenta jako wystaczającą, ustawia ocene lub/z uzasadnieniem.
Klient po tym weryfikuje czy ocena została wstawiona, i przechodzi do następnego stanu.
Dla stanów `evaluate_project_grade`, `evaluate_teammate_grade`,`evaluate_objectives`, `evaluate_assumption`, odpowiednie cele pytań (student,projekt,założenie) są brane z bazy, gdzie po każdej kolejnej udanej odpowiedzi studenta jest brany kolejny, nieoceniony cel.   
Przy stanie `evaluate_teammate_grade`, sprawdzana jest także mediana odpowiedzi innych studentów na temat osoby. Jeśli ocena studenta przekroczy granicę, agent przechodzi do substanu `outlier` i zadaje pytanie o różnice w odpowiedzi studenta do reszty. Uzasadnienie studenta jest także wpisywane do bazy.
Dla stanu `evaluate_assumption`, jeśli student odpowiedział że założenie zostało spełnione, a skrypt analizujący prezentacje oznaczył je jako niespełnione, zadawane jest mu pytanie `followup` o różnice odpowiedzi ze stanem bazy. Uzasadnienie studenta jest zapisywane do bazy.

Po każdej nie udanej odpowiedzi studenta agenta jest załączana podpowiedź, mówiąca o brakujących warunkach spełnienia pytania.

Po zakończeniu wszystkich pytań, student ma możliwość rozmowy z `PostInterviewAgent`, z którym może gadać o czymkolwiek. Rozmowa z tym agentem toczy się tak długo, aż nie będzie powiedziane "bezpieczne słowo" KONIEC. 

#### Technologie
- ### [Serwer MCP](agent_server))
  Serwer MCP udostępnia narzędzia oraz zasoby dla agenta do zapisywania ocen oraz stanu, komunikując się z bazą neo4j.
  
  
  #### Technologie
- ### Baza danych neo4j
- ### [Analiza Githuba](github_review)
- ### [Frontend aplikacji](frontend)
- ### [Backend aplikacji](backend)
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

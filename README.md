﻿# Steamy Stools
## Opis programu
Steamy stools to aplikacja mająca za zadanie automatyzacje procesy "Gorących Krzeseł", czyli wywiadów końcowych występujących na końcu przedmiotu ZSD.
Początkowo program ocenia wkład studentów w projektowe repozytoria Github, oraz wyciąga informacje na temat spełnienia założen na podstawie prezentacji początkowej i końcowej.

Po ocenieniu pracy i spełnienia założeń, możliwe jest przeprowadzenie rozmowy z agentem AI, w której agent pyta o oceny siebie, różnych osób, projektów, oraz o wkład na temat własnej przyszłości i feedback o przedmiocie. 

Po zakończeniu rozmowy z wszystkimi osobami, możliwa jest generacja końcowego raportu z wynikami.

## Działanie poszczególnych modułów
### [Klient rozmowy](agent_client)
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
### [Serwer MCP](agent_server)
  Serwer MCP udostępnia narzędzia oraz zasoby dla agenta do zapisywania ocen oraz stanu, komunikując się z bazą neo4j.
  
  
#### Technologie
##### Baza danych neo4j

Neo4j zawiera dane studentów, ich projektów zespołowych i wszystkich ocen jakie między sobą wystawiają (samoocena, oceny kolegów, lidera, projektu). Baza śledzi również założenia projektowe i ewaluacje studentów dotyczące ich spełnienia. Zapisywane są w niej również informacje śledzące obecny stan rozmowy. 

W celu zapewnienia wygodnej obsługi bazy danych w pliku [inicjalizacyjnym](agent_server/src/neo4j_retriever/__init__.py) zaimplementowane zostały 2 zestawy metod, set i get pozwalające na szybkie wyszukiwanie i sprawdzanie rekordów, oraz tworzenie nowych rekordów w bazie. Metody get pozwalają na wyszukiwanie informacji o danych uczestnikach poprzez różne identyfikatory w zależności od tego jakie informacje poosiada agent. Dodatkowo stworzone zostały również metody wypełniające bazę danych poprzez zaciągnięcie informacji z plików .csv. Jest to kluczowa funkcjonalność pozwalająca na ułatwienie dalszego testowania serwisu poprzez łatwe zmienianie stanu "przesłuchania". 

Opis etykiet bazy danych:
- Typy node'ów (Neo4j labels):
  - `Student`
    - name - imię
    - surname - nazwisko
    - index - numer indeksu
    - github - nick github
  - `Project`
    - id - identyfikator projektu
    - name - nazwa projektu
  - `Answer`
    - grade - ocena (liczba)
    - explanation - uzasadnienie oceny
    - question_type - typ pytania (self_assessment, teammate_assessment, project_assessment, leadership_assessment, objectives_assessment, github_assessment, masters_intent, study_program_feedback)
    - outlier_followup_done - czy dodano uzasadnienie dla opinii odbiegającej (boolean)
    - outlier_followup - tekst uzasadnienia
  - `Assumption`
    - description
    - system_accepted
  - `AssumptionEvaluation`
    - explanation
  - `ConversationSession`
    - session_id
    - student_index
    - current_state
    - last_state
    - pending_target_json
    - pending_substate_json
    - started_at
    - last_updated
    - is_active
    - completed
  - `ConversationMessage`
    - message_id
    - role
    - content 
    - state_at_time
    - timestamp

- Typy relacji (Neo4j relationship types):
  - `belongs_to`
  - `answered`
  - `refers_to`
  - `has_assumption`
  - `evaluated`
  - `HAS_SESSION`
  - `HAS_MESSAGE`

- Typy pytań / odpowiedzi (wartości `question_type`):
  - `self_assessment`
  - `teammate_assessment`
  - `github_assessment`
  - `leadership_assessment`
  - `project_assessment`
  - `objectives_assessment`
  - `masters_intent`
  - `study_program_feedback`

- Stany workflow (wartości `current_state`):
  - `initial`
  - `self_evaluation`
  - `evaluate_teammate_grade`
  - `evaluate_project_grade`
  - `evaluate_leader_grade`
  - `evaluate_objectives`
  - `evaluate_assumption`
  - `masters_intent`
  - `study_program_feedback`
  - `done`
  - `completed`

##### Generacja raportów i ocen końcowych
[generate_reports.py](agent_server/src/neo4j_retriever/generate_reports.py)

Generuje 14 kompleksowych raportów CSV z bazy Neo4j. Eksportuje wszystkie dane struktury bazy:
Węzły: studenci, projekty, założenia
Oceny: samooceny, projekty, współpracownicy, liderów, GitHub, cele
Ewaluacje założeń studentów
Podsumowania i statystyki. Każdy raport to osobny plik CSV z pełnym zrzutem danych danej kategorii.

[generate_final_grades.py](agent_server/src/neo4j_retriever/generate_final_grades.py)

Oblicza oceny końcowe studentów na podstawie ważonego wzoru:

Ocena = 0.10·Samoocena + 0.25·ŚrOcenWspółprac + 0.20·OcenaProjektu + 0.15·OcenaCelów + 0.15·OcenaGitHub + 0.15·WspółczynnikZałożeń

- Normalizuje brakujące dane
- Zapisuje wyniki do CSV z raportów

### [Analiza Githuba](backend)
####[Analiza Repozytoriów](backend/code_metrics.py)
####[Analiza Założeń](backend/objectives.py)

Zadaniem modułu analizy założeń jest automatyczne wykrywanie oraz weryfikacja założeń projektowych na podstawie dokumentów początkowych i końcowych projektu. Moduł działa w trybie wsadowym i jest uruchamiany niezależnie od klienta rozmowy, natomiast zapisane przez niego dane są później wykorzystywane w trakcie rozmowy ze studentem.

Analiza wykonywana jest na katalogu `assumptions`, w którym każdy projekt posiada osobny folder. Dla każdego projektu wymagane są dwa podkatalogi: `start_assumptions`, zawierający dokumenty opisujące początkowe założenia projektu, oraz `end_assumptions`, zawierający dokumenty końcowe (np. prezentacje podsumowujące).

Obsługiwane są pliki tekstowe `.txt`, `.md`, `.json` oraz pliki `.pdf`, z których treść jest automatycznie wyodrębniana .

Moduł korzysta z modelu LLM (`gpt-4o-mini`) w dwóch etapach:
- ekstrakcji założeń (niska, ale niezerowa temperatura),
- deterministycznej weryfikacji spełnienia założeń (temperatura 0).

---

##### Etapy przetwarzania

###### ETAP 0 – Identyfikacja projektu

Na podstawie dokumentów początkowych wyodrębniana jest nazwa projektu. Model zwraca wyłącznie jedną linię tekstu zawierającą nazwę projektu, która następnie wykorzystywana jest do powiązania założeń z odpowiednim węzłem `Project` w bazie danych Neo4j.

###### ETAP 1 – Ekstrakcja założeń

Z dokumentów początkowych projektu wykrywane są mierzalne wymagania/założenia. Każde założenie otrzymuje unikalny identyfikator (`REQ-XXX`) oraz opis tekstowy. Wynik ekstrakcji zapisywany jest lokalnie do pliku `objectives.json` w katalogu projektu.

Każde założenie zawiera:
- identyfikator wymagania,
- nazwę projektu,
- opis wymagania.

###### ETAP 2 – Weryfikacja założeń

W kolejnym kroku wykryte założenia są weryfikowane na podstawie dokumentów końcowych projektu. Dla każdego wymagania model zwraca binarną informację, czy zostało ono spełnione (`true/false`).

Wynik weryfikacji zapisywany jest lokalnie w pliku `raport.json` i zawiera dla każdego założenia informację o jego spełnieniu (`spelnione`).

---

###### Integracja z Neo4j

Po zakończeniu analizy wszystkich projektów, założenia zapisywane są do bazy danych Neo4j. Dla każdego projektu wyszukiwany jest odpowiadający mu węzeł `Project`, a następnie tworzone są węzły `Assumption`, połączone relacją `has_assumption`.

Każdy węzeł `Assumption` przechowuje:
- opis założenia,
- systemową ocenę spełnienia (`system_accepted`).

Jeśli projekt nie istnieje w bazie lub konfiguracja Neo4j nie jest dostępna, zapis założeń jest pomijany.

---


##### [Inicjalizacja katalogów założeń](backend/assumptions_dirs.py)

Przed uruchomieniem analizy założeń konieczne jest przygotowanie struktury katalogów dla wszystkich projektów. Odpowiada za to funkcja `create_assumption_dirs`, której zadaniem jest automatyczne utworzenie katalogów roboczych na podstawie listy projektów.

Funkcja odczytuje plik `data/projects.json`, zawierający listę projektów zdefiniowanych w systemie. Dla każdego projektu tworzona jest struktura katalogów w folderze bazowym `assumptions`:

```bash
assumptions/
 └── <project_name>/
     ├── start_assumptions/
     └── end_assumptions/
```

Katalog `start_assumptions` przeznaczony jest na dokumenty opisujące początkowe założenia projektu, natomiast `end_assumptions` na dokumenty końcowe, które służą do weryfikacji spełnienia tych założeń.

---

###### Rola w systemie rozmów

Założenia zapisane przez moduł analizy wykorzystywane są w stanie `evaluate_assumption` klienta rozmowy. Systemowa ocena spełnienia założenia porównywana jest z odpowiedzią studenta. W przypadku rozbieżności student proszony jest o uzasadnienie, które zapisywane jest w bazie jako dodatkowa informacja do danego założenia.


---


##### [Parser dokumentów](backend/pdf2txt.py)

Ekstrakcja treści z plików wejściowych realizowana jest przez pomocniczy moduł `pdf2txt`, wykorzystywany przez analizator założeń do ujednolicenia formatu danych wejściowych.

Funkcja `extract_text_from_file` przyjmuje ścieżkę do pliku i zwraca jego zawartość w postaci tekstu w formacie Markdown.

W obecnej wersji:
- natywnie wspierane są pliki PDF,
- pliki tekstowe (`.txt`, `.md`, `.json`) są odczytywane bezpośrednio jako fallback,
- pozostałe formaty (`.doc`, `.ppt`, itp.) nie są wspierane w środowisku Docker (Linux) i wymagają wcześniejszej konwersji do PDF.

Dla plików PDF wykorzystywane są biblioteki:
- `pymupdf` – do otwarcia dokumentu,
- `pymupdf4llm` – do konwersji treści PDF na Markdown, zoptymalizowany pod dalsze przetwarzanie przez modele LLM.

W przypadku błędu ekstrakcji lub nieobsługiwanego formatu, funkcja zwraca komunikat ostrzegawczy zamiast treści dokumentu, co pozwala zachować ciągłość przetwarzania bez przerywania analizy całego projektu.

Moduł ten jest wykorzystywany na etapie wczytywania dokumentów zarówno dla katalogów `start_assumptions`, jak i `end_assumptions`.


### [Frontend aplikacji](frontend)
Frontend jest zbudowany jako SPA (Single Page Application) przy użyciu React 19 z TypeScript. Jako bundler i dev server wykorzystywany jest Vite, zapewniający szybkie przeładowanie podczas developmentu.

Głównym punktem wejścia aplikacji jest plik [App.tsx](frontend/src/App.tsx), który definiuje routing i strukturę strony. Komunikacja z backendem realizowana jest na dwa sposoby:
- **REST API** - poprzez bibliotekę Axios, której konfiguracja znajduje się w pliku [api.ts](frontend/src/services/api.ts)
- **WebSocket** - natywne API przeglądarki do komunikacji w czasie rzeczywistym, używane do odbierania statusów analiz i powiadomień

Komponenty interfejsu użytkownika znajdują się w katalogu [components](frontend/src/components). Główne z nich to:
- [AdminPanel.tsx](frontend/src/components/AdminPanel.tsx) - panel administracyjny do zarządzania analizami i inicjalizowania bazy danych
- [ChatPanel.tsx](frontend/src/components/ChatPanel.tsx) - panel rozmowy ze studentem podczas wywiadu

Dodatkowo zintegrowano bibliotekę React Speech Recognition, umożliwiającą studentom dyktowanie odpowiedzi głosem zamiast pisania.

#### Technologie
- React 19, TypeScript, Vite, Axios, React Speech Recognition

### [Backend aplikacji](backend)
Backend jest serwerem HTTP/WebSocket zbudowanym na frameworku FastAPI. Cała logika serwera znajduje się w pliku [server_http.py](backend/server_http.py).

Serwer udostępnia endpoint WebSocket pod ścieżką `/ws`, zarządzany przez klasę [`ConnectionManager`](backend/server_http.py). Menedżer ten przechowuje listę aktywnych połączeń i umożliwia:
- Akceptowanie nowych połączeń WebSocket od klientów
- Broadcastowanie wiadomości do wszystkich podłączonych klientów jednocześnie
- Powiadamianie frontendu o postępie i statusie trwających analiz w czasie rzeczywistym
- Obsługę rozłączeń i czyszczenie nieaktywnych połączeń

#### Technologie
- FastAPI, WebSocket
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
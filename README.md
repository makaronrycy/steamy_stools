# Steamy Stools - Wywiad "Gorące Krzesła"

Aplikacja webowa do analizy repozytoriów GitHub i przeprowadzania wywiadów technicznych z wykorzystaniem LLM (ChatGPT).

## Założenia projektowe
[Link do dokumentacji](https://docs.google.com/document/d/1pUIsDrNBLr739lHy4pXupU8hbw-gXFo2pniAe6srB4s/edit?usp=sharing)

---

## 🚀 Jak uruchomić projekt

### 1. Wymagania wstępne
*   **Docker Desktop** zainstalowany i uruchomiony.
*   **Git** do pobrania repozytorium.
*   **Klucz OpenAI API** (potrzebny do działania czatu).

### 2. Pobranie repozytorium
```bash
git clone https://github.com/makaronrycy/steamy_stools.git
cd steamy_stools
git checkout feature/webapp-integration
```
*(Upewnij się, że jesteś na odpowiednim branchu, np. `feature/webapp-integration`)*

### 3. Konfiguracja środowiska (.env)
W głównym katalogu projektu utwórz plik `.env` i dodaj swój klucz API OpenAI:

```env
OPENAI_API_KEY=sk-proj-twoj-klucz-tutaj...
```

### 4. Uruchomienie aplikacji
Uruchom wszystkie serwisy za pomocą Docker Compose:

```bash
docker-compose up --build -d
```
*Pierwsze uruchomienie może potrwać kilka minut (budowanie obrazów).*

### 5. Dostęp do aplikacji

Po uruchomieniu aplikacja jest dostępna pod adresem:
👉 **Frontend:** [http://localhost:5173](http://localhost:5173)

Pozostałe serwisy:
*   **Backend API:** [http://localhost:8000](http://localhost:8000)
*   **SonarQube:** [http://localhost:9000](http://localhost:9000) (Login: `admin` / `admin`)
*   **Neo4j Browser:** [http://localhost:7474](http://localhost:7474)
*   **Agent Client:** [http://localhost:3000](http://localhost:3000)

### 6. Użycie aplikacji
1.  Otwórz aplikację w przeglądarce ([http://localhost:5173](http://localhost:5173)).
2.  Zobaczysz okno czatu na pełnym ekranie.
3.  Aby przejść do **Panelu Administratora** (analiza GitHub, inicjalizacja bazy), kliknij kłódkę w lewym górnym rogu.
### 7. Resetowanie środowiska
Aby zatrzymać aplikację i usunąć wszystkie dane (kontenery, wolumeny, sieć), użyj:

```bash
docker-compose down -v
```
To przywróci środowisko do stanu początkowego (wyczyści bazę danych).

Jeśli chcesz usunąć również zbudowane obrazy (czysty start):
```bash
docker-compose down -v --rmi all
```

import os
import sys
import stat
import shutil
import subprocess
import time
import requests
import pandas as pd

from pymongo import MongoClient
from git import Repo
from dotenv import load_dotenv
from sklearn.preprocessing import MinMaxScaler

from Detect_Useless_Commits import detect_useless_commits
from regularity_metrics import evaluate_commit_regularities

# Wczytaj zmienne środowiskowe (.env w katalogu backend)
load_dotenv()

# === ENV ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("OWNER")
REPO_NAME = os.getenv("REPO_NAME")
GIT_BRANCH = os.getenv("MAIN_BRANCH", "main")

MONGO_URI = os.getenv("MONGO_URI")

WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")
REPO_DIR = os.path.join(WORKSPACE_DIR, "repo")

GITHUB_URL = os.getenv("GITHUB_URL")

# Dla kontenera skanera adres hosta Windows/WSL2:
SONAR_HOST_URL = os.getenv("SONAR_HOST_URL", "http://host.docker.internal:9000")
SONAR_API_URL = os.getenv("SONAR_API_URL", "http://localhost:9000")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")

SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY", "Project")
SONAR_PROJECT_NAME = os.getenv("SONAR_PROJECT_NAME", "Project")

PROJECT_START_TIME = pd.to_datetime(os.getenv("PROJECT_START_TIME", "2024-01-01")).tz_localize(None)
WEEKS = int(os.getenv("WEEKS", "12"))

# === UTILS ===
def safe_rmtree(path: str) -> None:
    """
    Bezpieczne usuwanie katalogu z fallbackiem dla Windows (readonly pliki).
    W Pythonie 3.11 stosujemy onerror; onexc pojawił się dopiero w 3.12.
    """
    if not os.path.exists(path):
        return

    def _onerror(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    shutil.rmtree(path, onerror=_onerror)

def ensure_workspace() -> None:
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

def clone_repository() -> None:
    """
    Klonuje repo do WORKSPACE_DIR/repo; jeśli GITHUB_URL jest publiczne, token nie jest wymagany.
    """
    ensure_workspace()
    safe_rmtree(REPO_DIR)

    url = GITHUB_URL or f"https://github.com/{OWNER}/{REPO_NAME}.git"
    Repo.clone_from(url, REPO_DIR, branch=GIT_BRANCH)

def write_sonar_properties() -> None:
    """
    Tworzy sonar-project.properties w WORKSPACE_DIR, wskazując katalog źródeł na 'repo'.
    """
    props_path = os.path.join(WORKSPACE_DIR, "sonar-project.properties")
    with open(props_path, "w", encoding="utf-8") as f:
        f.write(
            f"sonar.projectKey={SONAR_PROJECT_KEY}\n"
            f"sonar.projectName={SONAR_PROJECT_NAME}\n"
            f"sonar.sources=repo\n"
            f"sonar.sourceEncoding=UTF-8\n"
        )

def run_sonar_scanner() -> None:
    """
    Uruchamia SonarScanner w kontenerze Docker.
    Uwierzytelnienie: SONAR_TOKEN (nie SONAR_LOGIN) + redundancja -Dsonar.token.
    """
    # Log diagnostyczny przed uruchomieniem skanera
    print(f"[DEBUG] Using SONAR_HOST_URL={SONAR_HOST_URL}, SONAR_TOKEN set={bool(SONAR_TOKEN)}")

    if not SONAR_TOKEN:
        raise RuntimeError("Brak SONAR_TOKEN w środowisku — wymagana autoryzacja do SonarQube.")

    write_sonar_properties()

    # Mapujemy WORKSPACE_DIR do /usr/src; skaner czyta /usr/src/sonar-project.properties
    volume_arg = f"{WORKSPACE_DIR}:/usr/src"

    cmd = [
        "docker", "run", "--rm",
        "-e", f"SONAR_HOST_URL={SONAR_HOST_URL}",
        "-e", f"SONAR_TOKEN={SONAR_TOKEN}",      # kluczowe: token przez zmienną środowiskową
        "-v", volume_arg,
        "sonarsource/sonar-scanner-cli",
        f"-Dsonar.token={SONAR_TOKEN}"           # redundancja: token również jako parametr
        # "-X"  # opcjonalnie pełny debug skanera
    ]

    subprocess.run(cmd, check=True)

def sonar_server_ready(timeout_sec: int = 180) -> bool:
    """
    Czeka aż SonarQube przejdzie do statusu UP przez API /api/system/status.
    """
    url = f"{SONAR_API_URL.rstrip('/')}/api/system/status"
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        try:
            r = requests.get(url, timeout=5)
            if r.ok:
                js = r.json()
                if js.get("status") == "UP":
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False

def save_results_to_mongo(payload: dict) -> None:
    """
    Przykładowy zapis wyników do MongoDB według MONGO_URI.
    """
    if not MONGO_URI:
        return
    client = MongoClient(MONGO_URI)
    db = client.get_database("GitHubDB")
    col = db.get_collection("score")
    col.insert_one(payload)

def full_github_review() -> None:
    """
    Główne wejście – wywoływane przez backend:
    - klonuje repo,
    - czeka na SonarQube=UP,
    - uruchamia skan SonarQube (Docker) z tokenem,
    - (opcjonalnie) liczy metryki commitów i regularności,
    - zapisuje wyniki do MongoDB.
    """
    # 1) Klon repo
    clone_repository()

    # 2) Poczekaj na SonarQube=UP, inaczej skaner może wyjść z błędem
    if not sonar_server_ready(timeout_sec=180):
        raise RuntimeError("SonarQube nie jest w stanie UP – sprawdź http://localhost:9000 i token.")

    # 3) Uruchom skaner (z poprawnym tokenem)
    run_sonar_scanner()

    # 4) (Przykład) Metryki commitów i regularności
    try:
        useless = detect_useless_commits(REPO_DIR)  # lista słowników
    except Exception:
        useless = []

    # 5) Przykładowy payload do bazy
    payload = {
        "repo": f"{OWNER}/{REPO_NAME}",
        "branch": GIT_BRANCH,
        "timestamp": pd.Timestamp.utcnow().to_pydatetime(),
        "useless_commits_found": len(useless),
        "details": {
            "sonar_host": SONAR_HOST_URL,
            "project_key": SONAR_PROJECT_KEY,
            "project_name": SONAR_PROJECT_NAME,
            "weeks": WEEKS,
            "project_start": str(PROJECT_START_TIME.date()),
        },
    }
    save_results_to_mongo(payload)

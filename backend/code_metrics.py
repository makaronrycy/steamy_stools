import os
import sys
import stat
import shutil
import subprocess
import time
import requests
import pandas as pd
import csv
import difflib
from datetime import datetime

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

WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", os.path.join(os.getcwd(), "workspace"))
REPO_DIR = os.path.join(WORKSPACE_DIR, "repo")

# Ścieżka do workspace na HOŚCIE (dla Docker-in-Docker wolumenów)
# W kontenerze WORKSPACE_DIR="/app/workspace", ale SonarScanner potrzebuje ścieżki hosta
HOST_WORKSPACE_DIR = os.getenv("HOST_WORKSPACE_DIR", WORKSPACE_DIR)

GITHUB_URL = os.getenv("GITHUB_URL")

# Dla kontenera skanera adres hosta Windows/WSL2:
SONAR_HOST_URL = os.getenv("SONAR_HOST_URL", "http://host.docker.internal:9000")
SONAR_API_URL = os.getenv("SONAR_API_URL", "http://localhost:9000")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")

SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY", "Project")
SONAR_PROJECT_NAME = os.getenv("SONAR_PROJECT_NAME", "unknown_project")
PROJECT_ID = os.getenv("PROJECT_ID", "1")  # Default to 1
csv_file_path = os.path.join(os.path.dirname(__file__), "data_no_grades.csv")

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

    # Mapujemy HOST_WORKSPACE_DIR do /usr/src; skaner czyta /usr/src/sonar-project.properties
    # Używamy HOST_WORKSPACE_DIR bo SonarScanner to osobny kontener Docker
    volume_arg = f"{HOST_WORKSPACE_DIR}:/usr/src"

    cmd = [
        "docker", "run", "--rm",
        "--network", "zsd20_zsd-network",         # aby mieć dostęp do sieci docker-compose
        "-e", f"SONAR_HOST_URL={SONAR_HOST_URL}",
        "-e", f"SONAR_TOKEN={SONAR_TOKEN}",      # kluczowe: token przez zmienną środowiskową
        "-v", volume_arg,
        "-u", "0",                               # Uruchom jako root, aby uniknąć problemów z uprawnieniami do plików
        "sonarsource/sonar-scanner-cli",
        f"-Dsonar.token={SONAR_TOKEN}"           # redundancja: token również jako parametr
        # "-X"  # opcjonalnie pełny debug skanera
    ]

    try:
        # Capture output to debug errors
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[DEBUG] SonarScanner finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] SonarScanner failed with exit code {e.returncode}")
        print(f"[ERROR] STDOUT:\n{e.stdout}")
        print(f"[ERROR] STDERR:\n{e.stderr}")
        raise e

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

def get_git_commit_data(repo_dir: str) -> list[dict]:
    """
    Pobiera dane o commitach (autor, data) z repozytorium Git.
    """
    try:
        git_cmd = ["git", "-C", repo_dir, "log", "--format=%an|%ad", "--date=short"]
        output = subprocess.check_output(git_cmd, text=True, encoding="utf-8", errors="replace")
        
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        
        data = []
        for line in lines:
            parts = line.split("|", 1)
            if len(parts) == 2:
                data.append({"author": parts[0], "date": parts[1]})
        return data
    except Exception as e:
        print(f"[ERROR] Failed to get git commit data: {e}")
        return []

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

    # 4) Metryki commitów i regularności
    try:
        useless = detect_useless_commits(REPO_DIR)  # lista słowników
    except Exception:
        useless = []

    try:
        # Load CSV and filter students by PROJECT_ID
        students_map = {}  # Map Name/Surname -> Index
        project_students = []
        if os.path.exists(csv_file_path):
            with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['project_id'] == PROJECT_ID:
                        # Create mapping keys from name and surname
                        full_name = f"{row['name']} {row['surname']}"
                        students_map[full_name.lower()] = row
                        students_map[row['name'].lower()] = row
                        students_map[row['surname'].lower()] = row
                        # Save student info for result template
                        project_students.append(row)
        else:
            print(f"[WARNING] CSV file not found at {csv_file_path}")

        commit_history = get_git_commit_data(REPO_DIR)
        
        # DataFrame conversion
        all_commits_df = pd.DataFrame(commit_history)
        if all_commits_df.empty:
            print("[INFO] No commits found.")
            dfs_names = []
        else:
            # Map git authors to students
            all_commits_df['student_index'] = None
            all_commits_df['student_name'] = None

            for idx, row in all_commits_df.iterrows():
                author_lower = row['author'].lower()
                # Try exact match first
                matched_student = None
                
                # Check against map
                for key_name, student_data in students_map.items():
                    if key_name in author_lower:
                        matched_student = student_data
                        break
                
                # Fallback: difflib for close matches if needed (optional, keeping simple for now)
                
                if matched_student:
                    all_commits_df.at[idx, 'student_index'] = matched_student['index']
                    all_commits_df.at[idx, 'student_name'] = f"{matched_student['name']} {matched_student['surname']}"
                else:
                    all_commits_df.at[idx, 'student_name'] = row['author'] # Keep original if no match

            # Group by student_index if available, otherwise fallback to author
            # Actually, we want to evaluate regularities for ALL project students
            dfs_names = []
            
            for student in project_students:
                s_index = student['index']
                # Filter commits for this student
                student_commits = all_commits_df[all_commits_df['student_index'] == s_index]
                if student_commits.empty:
                    # Also try matching by author name if index wasn't mapped (fallback)
                   full_name_lower = f"{student['name']} {student['surname']}".lower()
                   student_commits = all_commits_df[all_commits_df['author'].str.lower().str.contains(student['name'].lower()) | 
                                                    all_commits_df['author'].str.lower().str.contains(student['surname'].lower())]
                
                # If still empty, create empty DF but with 'date' column for the function
                if student_commits.empty:
                     student_commits = pd.DataFrame(columns=['date', 'author', 'student_index', 'student_name'])

                dfs_names.append(student_commits)

        # Prepare unique names list corresponding to project_students
        unique_names = [f"{s['name']} {s['surname']} ({s['index']})" for s in project_students]
        
        # If no CSV filtering happened (e.g. file missing), fallback to old logic
        if not project_students:
             unique_names = all_commits_df['author'].unique() if not all_commits_df.empty else []
             dfs_names = [all_commits_df[all_commits_df['author'] == author] for author in unique_names]

        # Calculate regularity
        reg_df = evaluate_commit_regularities(dfs_names, unique_names, PROJECT_START_TIME, WEEKS)
        
        # Add index to results if possible
        if not reg_df.empty and project_students:
             # Assuming order is preserved (zip in evaluate_commit_regularities)
             reg_df['student_index'] = [s['index'] for s in project_students]

        # Konwersja do dict (records)
        if not reg_df.empty:
            regularity_data = reg_df.to_dict(orient="records")
                
    except Exception as e:
        print(f"[ERROR] Regularity metrics failed: {e}")
        regularity_data = []

    # Oblicz średnią ocenę (GitHub Score)
    regularity_score = 0.0
    if regularity_data:
        scores = [d.get("regularity_score", 0) for d in regularity_data]
        if scores:
            regularity_score = sum(scores) / len(scores)

    # Oblicz ocenę za jakość commitów (Commit Score)
    # Wzór: 5.0 - (3.0 * (useless / total))
    # 0% useless -> 5.0
    # 100% useless -> 2.0
    total_commits_count = len(all_commits_df) if 'all_commits_df' in locals() and not all_commits_df.empty else 0
    
    if total_commits_count > 0:
        useless_ratio = len(useless) / total_commits_count
        commit_score = 5.0 - (3.0 * useless_ratio)
        if commit_score < 2.0:
            commit_score = 2.0
    else:
        commit_score = 2.0 # Brak commitów to ocena niedostateczna
        
    # Średnia ważona
    # 0.65 * regularity + 0.35 * commit
    weighted_score = (0.65 * regularity_score) + (0.35 * commit_score)
    
    def round_to_quarter(x):
        return round(x * 4) / 4
        
    final_score = round_to_quarter(weighted_score)

    # 5) Przykładowy payload do bazy
    payload = {
        "repo": f"{OWNER}/{REPO_NAME}",
        "branch": GIT_BRANCH,
        "timestamp": pd.Timestamp.utcnow().to_pydatetime(),
        "useless_commits_found": len(useless),
        "total_commits": total_commits_count,
        "regularity_metrics": regularity_data,
        "scores": {
            "regularity_score_avg": round(regularity_score, 2),
            "commit_score_avg": round(commit_score, 2),
            "final_score": final_score
        },
        "details": {
            "sonar_host": SONAR_HOST_URL,
            "project_key": SONAR_PROJECT_KEY,
            "project_name": SONAR_PROJECT_NAME,
            "weeks": WEEKS,
            "project_start": str(PROJECT_START_TIME.date()),
        },
    }
    save_results_to_mongo(payload)

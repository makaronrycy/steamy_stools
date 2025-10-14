import os
import subprocess
import time
import requests
import pandas as pd
from git import Repo
from dotenv import load_dotenv
from Detect_Useless_Commits import detect_useless_commits
load_dotenv()

# --- zmienne środowiskowe ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("OWNER")
REPO_NAME = os.getenv("REPO_NAME")
GIT_BRANCH = os.getenv("GIT_BRANCH", "main")

WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")
REPO_DIR = os.path.join(WORKSPACE_DIR, "repo")

GITHUB_URL = os.getenv("GITHUB_URL")

SONAR_HOST_URL = os.getenv("SONAR_HOST_URL", "http://host.docker.internal:9000")
SONAR_API_URL = os.getenv("SONAR_API_URL", "http://localhost:9000")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY", "Project")
SONAR_PROJECT_NAME = os.getenv("SONAR_PROJECT_NAME", "Project")

def load_commits():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    url = f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/commits"

    all_commits = []
    page = 1
    per_page = 100

    while True:
        params = {"sha": GIT_BRANCH, "per_page": per_page, "page": page}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        commits_page = response.json()
        if not commits_page:
            break
        
        for c in commits_page:
            all_commits.append({
                "sha": c["sha"],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"]
            })
        
        page += 1

    print(f"Znaleziono {len(all_commits)} commitów na branchu {GIT_BRANCH}.\n")

    df = pd.DataFrame(all_commits)
    df_sorted = df.sort_values(by = 'date', ascending = True).reset_index(drop = True)

    return df_sorted

def run_sonar_scanner():
    cmd = [
        "docker", "run", "--rm",
        "-e", f"SONAR_HOST_URL={SONAR_HOST_URL}",
        "-e", f"SONAR_LOGIN={SONAR_TOKEN}",
        "-v", f"{WORKSPACE_DIR}:/usr/src",
        "sonarsource/sonar-scanner-cli"
    ]

    subprocess.run(cmd, check=True)
    print("✅ Analiza SonarQube zakończona.")

def setup_workspace():
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

def create_sonar_properties_file(sonar_project_commit):

    file_path = os.path.join(WORKSPACE_DIR, "sonar-project.properties")
    content = f"""# --- Automatycznie wygenerowany plik SonarQube ---
    sonar.projectKey={sonar_project_commit}
    sonar.projectName={sonar_project_commit}
    sonar.sources=repo
    sonar.sourceEncoding=UTF-8
    sonar.host.url={SONAR_HOST_URL}
    sonar.login={SONAR_TOKEN}
    sonar.python.version=3

    # Wykluczenia z analizy
    sonar.exclusions=**/*.csv,**/venv/**,**/*.json,**/*.xml,**/*.yml,**/*.yaml,**/*.png,**/*.jpg,**/*.md,**/*.ico
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path

def clone_repository():

    if os.path.exists(REPO_DIR):
        return Repo(REPO_DIR)
    
    repo = Repo.clone_from(GITHUB_URL, REPO_DIR)
    return repo

def get_sonar_metrics(project_key):


    url = f"{SONAR_API_URL}/api/measures/component"
    params = {
        "component": project_key,
        "metricKeys": "bugs,vulnerabilities,code_smells,duplicated_lines_density"
    }

    response = requests.get(url, auth=(SONAR_TOKEN, ""), params=params)
    response.raise_for_status()
    data = response.json()

    measures = {m["metric"]: m["value"] for m in data["component"]["measures"]}
    return measures


def wait_for_sonar_analysis(project_key, timeout=180):
    
    start = time.time()
    
    while True:
        url = f"{SONAR_API_URL}/api/ce/component?component={project_key}"
        r = requests.get(url, auth=(SONAR_TOKEN, ""))
        r.raise_for_status()
        data = r.json()

        current_task = data.get("current")
        if current_task and current_task.get("status") == "SUCCESS":
            return 

        queue_tasks = data.get("queue", [])
        for task in queue_tasks:
            task_id = task["id"]
            status_url = f"{SONAR_API_URL}/api/ce/task?id={task_id}"
            r_status = requests.get(status_url, auth=(SONAR_TOKEN, ""))
            r_status.raise_for_status()
            status = r_status.json()["task"]["status"]
            if status == "SUCCESS":
                return

        if time.time() - start > timeout:
            raise TimeoutError("Analiza SonarQube nie zakończyła się w czasie")

        time.sleep(2)

def delete_sonar_project(project_key):

    url = f"{SONAR_API_URL}/api/projects/delete"
    response = requests.post(url, auth=(SONAR_TOKEN, ""), params={"project": project_key})
    if response.status_code == 204:
        print(f"Projekt '{project_key}' został usunięty.")
    else:
        print(f"Nie udało się usunąć projektu '{project_key}'. Status: {response.status_code}, odpowiedź: {response.text}")
    
def reset_to_latest_and_detect(repo):
 
    # Przywracanie repozytorium do najnowszego commita z gałęzi {GIT_BRANCH}
    repo.git.checkout(GIT_BRANCH)
    repo.remotes.origin.pull()
    
    # Uruchamianie detekcji bezużytecznych commitów
    detect_useless_commits()  
    return results
    
    
if __name__ == "__main__":
    commits = load_commits()
    setup_workspace()
    repo = clone_repository()
    commits_len = len(commits)
    commit_key = SONAR_PROJECT_KEY
    results = reset_to_latest_and_detect(repo)
    create_sonar_properties_file(commit_key)
    print(f"Znaleziono {commits_len} commitów.")
    
    
    oldest_commit = commits.iloc[0]["sha"]
    all_metrics = []
    
    for i in range(commits_len):
        commit = commits.iloc[i]["sha"]
        repo.git.checkout(commit)
        run_sonar_scanner()
        wait_for_sonar_analysis(commit_key)
        metrics = get_sonar_metrics(commit_key)
        if i != commits_len - 1:
            delete_sonar_project(commit_key)
        print("\n", metrics)
        all_metrics.append(metrics)
    print("\n", all_metrics)
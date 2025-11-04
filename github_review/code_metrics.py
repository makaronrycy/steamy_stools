import os
import subprocess
import time
import requests
import pandas as pd
import shutil
import stat
from pymongo import MongoClient
from git import Repo
from dotenv import load_dotenv
from Detect_Useless_Commits import detect_useless_commits
from sklearn.preprocessing import MinMaxScaler
from regularity_metrics import evaluate_commit_regularities

load_dotenv()

# Env variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("OWNER")
REPO_NAME = os.getenv("REPO_NAME")
GIT_BRANCH = os.getenv("MAIN_BRANCH", "main")
GIT_BRANCH = os.getenv("MAIN_BRANCH", "main")

MONGO_URI = os.getenv("MONGO_URI")
WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")
REPO_DIR = os.path.join(WORKSPACE_DIR, "repo")

GITHUB_URL = os.getenv("GITHUB_URL")

SONAR_HOST_URL = os.getenv("SONAR_HOST_URL", "http://host.docker.internal:9000")
SONAR_API_URL = os.getenv("SONAR_API_URL", "http://localhost:9000")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY")
SONAR_PROJECT_NAME = os.getenv("SONAR_PROJECT_NAME", "Project")

PROJECT_START_TIME = pd.to_datetime(os.getenv("PROJECT_START_TIME")).tz_localize(None)
WEEKS = int(os.getenv("WEEKS"))




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

def remove_repo_dir(repo_dir):

    def on_rm_error(func, path, exc_info):
        # zdejmujemy atrybut 'read-only' i próbujemy usunąć ponownie
        os.chmod(path, stat.S_IWRITE)
        os.remove(path)

    if os.path.exists(repo_dir):
        try:
            shutil.rmtree(repo_dir, onexc=on_rm_error)
            print(f"Usunięto folder: {repo_dir}")
        except Exception as e:
            print(f"Nie udało się całkowicie usunąć {repo_dir}: {e}")

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
    repo.git.checkout(GIT_BRANCH)
    repo.remotes.origin.pull()
    current_dir = os.getcwd()

    try:
        os.chdir(REPO_DIR)
        results = detect_useless_commits()

    finally:
        os.chdir(current_dir)

    return results
    
def save_to_database(client, data):
    github_db = client["GitHubDB"]
    
    useless_commits = github_db["useless_commits"]
    useless_commits.create_index("sha", unique=True)
    useless_commits.insert_many(data)


def date_preprocessing(data):

    unique_names = data["author"].unique()
    dfs =[]
    for name in unique_names:
        df = data[data['author'] == name].sort_values(by = 'date', ascending = True).reset_index(drop = True)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.tz_localize(None)
        dfs.append(df)

    return dfs, unique_names


def metrics_processing(metrics_df):
   
   cols = ['bugs','vulnerabilities', 'code_smells', 'duplicated_lines_density']

   metrics_df['date'] = pd.to_datetime(metrics_df['date'], errors='coerce').dt.tz_localize(None)
   
   orig = metrics_df[cols].copy()

   metrics_df[cols] = metrics_df[cols].apply(pd.to_numeric, errors='coerce')

   metrics_df[cols] = metrics_df[cols].diff()
   metrics_df[cols] = metrics_df[cols].fillna(orig)
   
def normalize_metrics(df):
    cols = ['bugs','vulnerabilities','code_smells','duplicated_lines_density']
    scaler = MinMaxScaler()
    df[cols] = scaler.fit_transform(df[cols])
    return df

def compute_commit_score(df):
    weights = {
        'bugs': 0.4,
        'vulnerabilities': 0.3,
        'code_smells': 0.2,
        'duplicated_lines_density': 0.1
    }

    df['commit_score'] = (
        df['bugs'] * weights['bugs'] +
        df['vulnerabilities'] * weights['vulnerabilities'] +
        df['code_smells'] * weights['code_smells'] +
        df['duplicated_lines_density'] * weights['duplicated_lines_density']
    )

      # Skala 0–1 (im wyższa, tym lepiej)
    df['commit_score'] = 1 - (df['commit_score'] - df['commit_score'].min()) / (df['commit_score'].max() - df['commit_score'].min() + 1e-9)
    df['commit_score'] = 2+df['commit_score'] * (5-2) 
    
    return df

def evaluate_commits(metrics_df, useless_commits):
    metrics_df = normalize_metrics(metrics_df)
    metrics_df = compute_commit_score(metrics_df)
    return metrics_df

if __name__ == "__main__":

    remove_repo_dir(REPO_DIR)
    
    commits = load_commits()
    
    setup_workspace()
    
    repo = clone_repository()
    
    commit_key = SONAR_PROJECT_KEY
    
    useless_commits = reset_to_latest_and_detect(repo)
    
    for useless_commit in useless_commits:
        
        commits = commits[commits['sha'] != useless_commit['sha']]
        print("\n", useless_commit)
    
    commits.reset_index(drop = True, inplace = True)
    commits_len = len(commits)
    client = MongoClient(MONGO_URI)
    #save_to_database(client, useless_commits)
    
    create_sonar_properties_file(commit_key)
    print(f"Znaleziono {commits_len} commitów.")
    
    
    oldest_commit = commits.iloc[0]["sha"]
    all_metrics = []
    for i in range(commits_len-1):

        commit = commits.iloc[i]["sha"]
        repo.git.checkout(commit)

        run_sonar_scanner()
        wait_for_sonar_analysis(commit_key)
        metrics = get_sonar_metrics(commit_key)
        metrics["sha"] = commits.iloc[i]["sha"]
        metrics["author"] = commits.iloc[i]["author"]
        metrics["date"] = commits.iloc[i]["date"]
        
        delete_sonar_project(commit_key)
        all_metrics.append(metrics)
        

    dfs_names, unique_names = date_preprocessing(commits)

    metrics_df = pd.DataFrame(all_metrics)
    metrics_df['date'] = pd.to_datetime(metrics_df['date'], errors='coerce').dt.tz_localize(None)
    metrics_df.sort_values(by = 'date', ascending = True, inplace = True)
    

    metrics_processing(metrics_df)
    regularity_df = evaluate_commit_regularities(dfs_names.copy(), unique_names.copy(), PROJECT_START_TIME, WEEKS)
    print(metrics_df.to_string())
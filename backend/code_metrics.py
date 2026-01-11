import os
import subprocess
import time
import requests
import pandas as pd
import shutil
import stat
import json
from pymongo import MongoClient
from git import Repo
from dotenv import load_dotenv
from sklearn.preprocessing import MinMaxScaler
from Detect_Useless_Commits import detect_useless_commits
from regularity_metrics import evaluate_commit_regularities
from pathlib import Path
from urllib.parse import urlparse
load_dotenv()

# Env variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("OWNER")
REPO_NAME = os.getenv("REPO_NAME")
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




def load_commits(github_token, owner, repo_name, git_branch):
    headers = {
    "Authorization": f"token {github_token}",
    "Accept": "application/vnd.github+json"
    }

    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"

    all_commits = []
    page = 1
    per_page = 100

    while True:
        params = {"sha": git_branch, "per_page": per_page, "page": page}
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
    
    # TEMP: Limit to last 3 commits for testing
    df_sorted = df_sorted.tail(3).reset_index(drop=True)

    return df_sorted

HOST_WORKSPACE_DIR = os.getenv("HOST_WORKSPACE_DIR", WORKSPACE_DIR)
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "steamy_stools_steamy-network")

def run_sonar_scanner():
    print(f"[DEBUG] Starting SonarScanner via Docker. Volume: {HOST_WORKSPACE_DIR}:/usr/src, Network: {DOCKER_NETWORK}")
    cmd = [
        "docker", "run", "--rm",
        "--network", DOCKER_NETWORK,
        "-e", f"SONAR_HOST_URL={SONAR_HOST_URL}",
        "-e", f"SONAR_LOGIN={SONAR_TOKEN}",
        "-e", f"SONAR_TOKEN={SONAR_TOKEN}", 
        "-v", f"{HOST_WORKSPACE_DIR}:/usr/src",
        "sonarsource/sonar-scanner-cli",
        f"-Dsonar.token={SONAR_TOKEN}"
    ]

    try:
        # Capture output to diagnose the error (e.g. "sonar-project.properties not found")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] SonarScanner failed. Exit Code: {e.returncode}")
        print(f"[ERROR] STDOUT:\n{e.stdout}")
        print(f"[ERROR] STDERR:\n{e.stderr}")
        raise e


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

def clone_repository(clean_url, github_token):
    if os.path.exists(REPO_DIR):
        return Repo(REPO_DIR)

    # https://github.com/owner/repo
    # ↓
    # https://TOKEN@github.com/owner/repo
    auth_url = clean_url.replace(
        "https://github.com/",
        f"https://{github_token}@github.com/"
    )

    repo = Repo.clone_from(auth_url, REPO_DIR)
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
        os.chmod(path, stat.S_IWRITE)
        os.remove(path)

    if os.path.exists(repo_dir):
        try:
            shutil.rmtree(repo_dir, onerror=on_rm_error)
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
    
def reset_to_latest_and_detect(repo, git_branch):
    repo.git.checkout(git_branch)
    repo.remotes.origin.pull()
    
    # detect_useless_commits now accepts repo_path 
    return detect_useless_commits(REPO_DIR)
    
def db_save(client, db_name:str, table_name:str, data):
    github_db = client[db_name]
    db = github_db[table_name]

    db.delete_many({})

    if not data.empty:
        db.insert_many(data.to_dict("records"))


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
    df['commit_score'] = 2+df['commit_score'] * 3 
    
    return df

def evaluate_commits(metrics_df, useless_commits):
    metrics_df = normalize_metrics(metrics_df)
    metrics_df = compute_commit_score(metrics_df)
    return metrics_df

def full_github_review():


    
    api_keys = []
    names = []
    owners = []
    project_names = []
    branches = []
    clean_urls = []
    input_path = Path("/app/data/projects.json")
    with open(input_path, "r", encoding="utf-8") as f:
        projects = json.load(f)



    for item in projects:
        names.append(item["name"])
        api_keys.append(item["api_key"])
        github_url = item["github"]
        parsed_url = urlparse(github_url)

        path_parts = parsed_url.path.strip("/").split("/")

        owner = path_parts[0]
        project_name = path_parts[1]
        branch = path_parts[3]

        clean_url = github_url.split("/tree/")[0]
        clean_urls.append(clean_url)
        owners.append(owner)
        project_names.append(project_name)
        branches.append(branch)


    print("\n", api_keys, owners, project_names, branches)
    print("\n", GITHUB_TOKEN, OWNER, REPO_NAME, GIT_BRANCH)

    for owner, project_name, branch, name, api_key, clean_url in zip(owners, project_names, branches, names, api_keys, clean_urls):

        print("\n", api_key, owner, project_name, branch)
        print("\n", GITHUB_TOKEN, OWNER, REPO_NAME, GIT_BRANCH)
        remove_repo_dir(REPO_DIR)

        commits = load_commits(api_key, owner, project_name, branch)
        
        setup_workspace()
        
        repo = clone_repository(clean_url, api_key)
        
        commit_key = SONAR_PROJECT_KEY
        
        useless_commits = reset_to_latest_and_detect(repo, branch)
        
        for useless_commit in useless_commits:
            
            commits = commits[commits['sha'] != useless_commit['sha']]
        
        commits.reset_index(drop = True, inplace = True)
        commits_len = len(commits)
        print("/n",commits_len, "------------------")
        create_sonar_properties_file(commit_key)
        
        
        oldest_commit = commits.iloc[0]["sha"]
        all_metrics = []
        #commits_len
        for i in range(3):

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

        metrics_scored_df = evaluate_commits(metrics_df.copy(), useless_commits)
        avg_scores_raw = metrics_scored_df.groupby('author')['commit_score'].mean().reset_index()
        avg_scores_raw['commit_score'] = (avg_scores_raw['commit_score'] / 0.25).round() * 0.25
        merged = pd.merge(regularity_df, avg_scores_raw, on="author", how="outer")

        merged['final_score'] = (merged['regularity_score'] * 0.65) + (merged['commit_score'] * 0.35)
        merged['final_score'] = (merged['final_score'] / 0.25).round() * 0.25
        avg_scores = merged[['author', 'final_score', 'regularity_score', 'commit_score']].copy()

        #NEO4J SAVE OR DATA PASS TO SOMEONE
        #client = MongoClient(MONGO_URI)
        #db_save(client,"GitHubDB","score", avg_scores)
        remove_repo_dir(REPO_DIR)
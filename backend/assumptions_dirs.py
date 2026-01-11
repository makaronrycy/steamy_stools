import os
import json
from pathlib import Path
from fastapi import FastAPI


app = FastAPI(title="Make directories", version="1.0")
@app.post("/make_dirs")
def make_directories():
    #input_path = Path("/app/data/projects.json")
    with open("data/projects.json", "r", encoding="utf-8") as f:
        projects = json.load(f)

    os.makedirs("assumptions", exist_ok=True)
    for project in projects:
        project_name = project["name"]
        os.makedirs(f"assumptions/{project_name}", exist_ok=True)
        os.makedirs(f"assumptions/{project_name}/start_assumptions")
        os.makedirs(f"assumptions/{project_name}/end_assumptions")
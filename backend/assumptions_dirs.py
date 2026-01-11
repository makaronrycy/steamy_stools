import os
import json
from pathlib import Path

def create_assumption_dirs():
    try:
        # Use absolute paths or relative to execution context (backend container workdir is /app)
        # We assume we are running from 'backend' directory or mapped to /app
        base_dir = Path(os.getcwd())
        projects_file = base_dir / "data" / "projects.json"
        
        if not projects_file.exists():
            # Fallback for local testing maybe?
            return {"status": "error", "message": f"File not found: {projects_file}"}

        with open(projects_file, "r", encoding="utf-8") as f:
            projects = json.load(f)

        assumptions_root = base_dir / "assumptions"
        os.makedirs(assumptions_root, exist_ok=True)
        
        created_count = 0
        for project in projects:
            project_name = project.get("name")
            if not project_name:
                continue
                
            proj_dir = assumptions_root / project_name
            os.makedirs(proj_dir, exist_ok=True)
            os.makedirs(proj_dir / "start_assumptions", exist_ok=True)
            os.makedirs(proj_dir / "end_assumptions", exist_ok=True)
            created_count += 1
            
        return {
            "status": "success", 
            "message": f"Katalogi zostały utworzone dla {created_count} projektów. Proszę umieścić pliki PDF lub PPTX w odpowiednim folderze (assumptions/[projekt]/start_assumptions)."
        }
    except Exception as e:
        return {"status": "error", "message": f"Błąd podczas tworzenia katalogów: {str(e)}"}
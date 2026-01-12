import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pdf2txt import extract_text_from_file

# =====================
# KONFIGURACJA
# =====================

BASE_PROJECTS_DIR = "assumptions"

MODEL = "gpt-4o-mini"
TEMPERATURE_EKSTRAKCJA = 0.1
TEMPERATURE_WERYFIKACJA = 0.0

load_dotenv()
client = OpenAI()

# =====================
# UTILS
# =====================

def read_all_files_from_dir(directory):
    texts = []

    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)

        if filename.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8") as f:
                texts.append(f.read())

        elif filename.lower().endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx")):
            try:
                texts.append(extract_text_from_file(path))
            except Exception as e:
                print(f" Błąd PDF {filename}: {e}")

    return "\n\n".join(texts)

def load_assumptions_to_neo4j(assumptions):
    if not assumptions:
        print("Brak zalozen do zapisania w Neo4j.")
        return

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("Brak biblioteki neo4j. Pomijam zapis zalozen do bazy.")
        return

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        print("Brak konfiguracji Neo4j w zmiennych srodowiskowych.")
        return

    driver = GraphDatabase.driver(uri, auth=(username, password))
    created_count = 0

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Project)
                RETURN p.id as project_id, p.name as project_name
            """)
            project_name_to_id = {
                record["project_name"]: record["project_id"] for record in result
            }

            for assumption in assumptions:
                project_name = assumption.get("projekt", "")
                description = assumption.get("opis", "")
                system_accepted = assumption.get("spelnione", False)

                project_id = project_name_to_id.get(project_name)
                if not project_id:
                    print(f"Warning: Project '{project_name}' not found in database, skipping assumptions")
                    continue

                if description:
                    session.run("""
                        MATCH (project:Project {id: $project_id})
                        CREATE (project)-[:has_assumption]->(assumption:Assumption {
                            description: $description,
                            system_accepted: $system_accepted
                        })
                    """,
                        project_id=project_id,
                        description=description,
                        system_accepted=system_accepted
                    )
                    created_count += 1
    finally:
        driver.close()

    print(f"Zapisano {created_count} zalozen do Neo4j.")


# =====================
# ETAP 0 – NAZWA PROJEKTU
# =====================

def extract_project_name(tekst):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Wyodrębnij nazwę projektu z dokumentu.\n"
                    "Zwróć WYŁĄCZNIE nazwę projektu jako jedną linię."
                )
            },
            {"role": "user", "content": tekst}
        ]
    )
    return response.choices[0].message.content.strip()

# =====================
# ETAP 1 – EKSTRAKCJA WYMAGAŃ
# =====================

def extract_objectives(tekst, project_name):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE_EKSTRAKCJA,
        messages=[
            {
                "role": "system",
                "content": (
                    f"Jesteś analitykiem wymagań dla projektu: {project_name}.\n"
                    "Zwróć WYŁĄCZNIE listę wymagań – po jednej linii.\n"
                    "Format: REQ-XXX: opis\n"
                    "Tylko wymagania mierzalne."
                )
            },
            {"role": "user", "content": tekst}
        ]
    )

    objectives = []
    for line in response.choices[0].message.content.splitlines():
        if ":" in line:
            req_id, opis = line.split(":", 1)
            objectives.append({
                "id": req_id.strip(),
                "projekt": project_name,
                "opis": opis.strip()
            })
    return objectives

# =====================
# ETAP 2 – WERYFIKACJA
# =====================

def verify_objectives(objectives, text_end):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE_WERYFIKACJA,
        messages=[
            {
                "role": "system",
                "content": (
                    "Jesteś audytorem.\n"
                    "Dla każdego wymagania zwróć:\n"
                    "REQ-XXX | true / false\n"
                    "Bez komentarzy."
                )
            },
            {
                "role": "user",
                "content": (
                    "WYMAGANIA:\n" +
                    "\n".join(f"{w['id']}: {w['opis']}" for w in objectives) +
                    "\n\nTEKST KOŃCOWY:\n" + text_end
                )
            }
        ]
    )

    results = {}
    for line in response.choices[0].message.content.splitlines():
        if "|" in line:
            req_id, status = line.split("|", 1)
            results[req_id.strip()] = status.strip().lower() == "true"

    return [
        {
            "id": w["id"],
            "projekt": w["projekt"],
            "opis": w["opis"],
            "spelnione": results.get(w["id"], False)
        }
        for w in objectives
    ]

# =====================
# MAIN – PRZETWARZANIE WIELU PROJEKTÓW
# =====================

def analyze_assumptions():
    """
    Core logic for analyzing assumptions.
    Returns: Dict with summary of processed projects.
    """
    processed_count = 0
    errors = []
    all_assumptions = []
    
    # Absolute path inside docker
    base_dir = os.path.join(os.getcwd(), BASE_PROJECTS_DIR)
    
    if not os.path.exists(base_dir):
        return {"status": "error", "message": f"Katalog {BASE_PROJECTS_DIR} nie istnieje. Najpierw utwórz katalogi."}

    for project_name in os.listdir(base_dir):
        # Full path construction
        project_path = os.path.join(base_dir, project_name)

        if not os.path.isdir(project_path):
            continue

        print(f"\n=== Projekt: {project_name} ===")

        start_dir = os.path.join(project_path, "start_assumptions")
        end_dir = os.path.join(project_path, "end_assumptions")

        if not os.path.isdir(start_dir) or not os.path.isdir(end_dir):
            print(" Brak wymaganych folderów – pomijam")
            continue

        try:
            text_project = read_all_files_from_dir(start_dir)
            
            # Skip if no content
            if not text_project.strip():
                 print(f"Brak plików w {start_dir}")
                 continue
                 
            text_end = read_all_files_from_dir(end_dir)

            # Analyze
            extracted_name = extract_project_name(text_project)
            objectives = extract_objectives(text_project, extracted_name)

            with open(os.path.join(project_path, "objectives.json"), "w", encoding="utf-8") as f:
                json.dump(objectives, f, indent=2, ensure_ascii=False)

            raport = verify_objectives(objectives, text_end)

            with open(os.path.join(project_path, "raport.json"), "w", encoding="utf-8") as f:
                json.dump(raport, f, indent=2, ensure_ascii=False)

            all_assumptions.extend(raport)
                
            processed_count += 1
            
        except Exception as e:
            msg = f"Błąd w projekcie {project_name}: {str(e)}"
            print(msg)
            errors.append(msg)

    if all_assumptions:
        load_assumptions_to_neo4j(all_assumptions)

    return {
        "status": "success", 
        "message": f"Przeanalizowano {processed_count} projektów.",
        "errors": errors
    }

if __name__ == "__main__":
    analyze_assumptions()

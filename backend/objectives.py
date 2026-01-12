#!/usr/bin/env python3
"""
assumption_analyzer.py

Moduł do analizy założeń projektowych na podstawie dokumentacji
wejściowej i końcowej.

Dla każdego projektu:
- wczytuje dokumenty początkowe (start_assumptions)
- ekstrahuje nazwę projektu
- identyfikuje mierzalne wymagania (założenia)
- weryfikuje ich spełnienie na podstawie dokumentów końcowych
- zapisuje wyniki do plików JSON
- opcjonalnie zapisuje dane do bazy Neo4j

Moduł przystosowany do przetwarzania wielu projektów
w strukturze katalogowej.
"""

import os
import json
from typing import List, Dict

from openai import OpenAI
from dotenv import load_dotenv
from pdf2txt import extract_text_from_file

# =====================
# KONFIGURACJA
# =====================

BASE_PROJECTS_DIR = "assumptions"
"""
Nazwa katalogu bazowego zawierającego podkatalogi projektów.

Każdy projekt powinien zawierać:
- start_assumptions/
- end_assumptions/
"""

MODEL = "gpt-4o-mini"
"""
Model OpenAI wykorzystywany do analizy treści dokumentów.
"""

TEMPERATURE_EKSTRAKCJA = 0.1
"""
Temperatura dla etapu ekstrakcji wymagań.
Niska wartość = minimalna kreatywność.
"""

TEMPERATURE_WERYFIKACJA = 0.0
"""
Temperatura dla etapu weryfikacji wymagań.
Wartość 0 zapewnia deterministyczne odpowiedzi.
"""

load_dotenv()
client = OpenAI()

# =====================
# UTILS
# =====================

def read_all_files_from_dir(directory: str) -> str:
    """
    Wczytuje i łączy treść wszystkich obsługiwanych plików z katalogu.

    Obsługiwane formaty:
    - .txt
    - .pdf, .doc, .docx, .ppt, .pptx

    Parameters
    ----------
    directory : str
        Ścieżka do katalogu z plikami.

    Returns
    -------
    str
        Połączona treść wszystkich plików.
    """
    texts: List[str] = []

    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)

        if filename.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8") as f:
                texts.append(f.read())

        elif filename.lower().endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx")):
            try:
                texts.append(extract_text_from_file(path))
            except Exception as e:
                print(f"[WARNING] Nie udało się odczytać pliku {filename}: {e}")

    return "\n\n".join(texts)


def load_assumptions_to_neo4j(assumptions: List[Dict]) -> None:
    """
    Zapisuje założenia projektowe do bazy danych Neo4j.

    Każde założenie jest łączone z istniejącym węzłem Project
    relacją :has_assumption.

    Oczekiwany format założenia:
    {
        "projekt": str,
        "opis": str,
        "spelnione": bool
    }

    Parameters
    ----------
    assumptions : list[dict]
        Lista słowników opisujących założenia projektowe.
    """
    if not assumptions:
        print("[INFO] Brak założeń do zapisania w Neo4j.")
        return

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("[WARNING] Brak biblioteki neo4j — pomijam zapis do bazy.")
        return

    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not username or not password:
        print("[WARNING] Brak konfiguracji Neo4j w zmiennych środowiskowych.")
        return

    driver = GraphDatabase.driver(uri, auth=(username, password))
    created_count = 0

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Project)
                RETURN p.id AS project_id, p.name AS project_name
            """)

            project_name_to_id = {
                record["project_name"]: record["project_id"]
                for record in result
            }

            for assumption in assumptions:
                project_name = assumption.get("projekt")
                description = assumption.get("opis")
                system_accepted = assumption.get("spelnione", False)

                project_id = project_name_to_id.get(project_name)
                if not project_id:
                    print(f"[WARNING] Projekt '{project_name}' nie istnieje w bazie.")
                    continue

                if description:
                    session.run("""
                        MATCH (project:Project {id: $project_id})
                        CREATE (project)-[:has_assumption]->(:Assumption {
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

    print(f"[INFO] Zapisano {created_count} założeń do Neo4j.")

# =====================
# ETAP 0 – NAZWA PROJEKTU
# =====================

def extract_project_name(text: str) -> str:
    """
    Wyodrębnia nazwę projektu z dokumentacji przy użyciu LLM.

    Parameters
    ----------
    text : str
        Pełna treść dokumentów projektu.

    Returns
    -------
    str
        Nazwa projektu.
    """
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
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip()

# =====================
# ETAP 1 – EKSTRAKCJA WYMAGAŃ
# =====================

def extract_objectives(text: str, project_name: str) -> List[Dict]:
    """
    Ekstrahuje mierzalne wymagania projektowe z dokumentacji.

    Parameters
    ----------
    text : str
        Treść dokumentów wejściowych.
    project_name : str
        Nazwa projektu.

    Returns
    -------
    list[dict]
        Lista wymagań w formacie:
        {
            "id": str,
            "projekt": str,
            "opis": str
        }
    """
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
            {"role": "user", "content": text}
        ]
    )

    objectives: List[Dict] = []

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

def verify_objectives(objectives: List[Dict], text_end: str) -> List[Dict]:
    """
    Weryfikuje spełnienie wymagań na podstawie dokumentacji końcowej.

    Parameters
    ----------
    objectives : list[dict]
        Lista wymagań wyekstrahowanych w etapie 1.
    text_end : str
        Treść dokumentów końcowych projektu.

    Returns
    -------
    list[dict]
        Lista wymagań wraz z polem 'spelnione'.
    """
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

    results: Dict[str, bool] = {}

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
# MAIN
# =====================

def analyze_assumptions() -> Dict:
    """
    Przetwarza wszystkie projekty w katalogu bazowym.

    Returns
    -------
    dict
        Podsumowanie procesu analizy.
    """
    processed_count = 0
    errors: List[str] = []
    all_assumptions: List[Dict] = []

    base_dir = os.path.join(os.getcwd(), BASE_PROJECTS_DIR)

    if not os.path.exists(base_dir):
        return {
            "status": "error",
            "message": f"Katalog {BASE_PROJECTS_DIR} nie istnieje."
        }

    for project_name in os.listdir(base_dir):
        project_path = os.path.join(base_dir, project_name)

        if not os.path.isdir(project_path):
            continue

        print(f"\n=== Projekt: {project_name} ===")

        start_dir = os.path.join(project_path, "start_assumptions")
        end_dir = os.path.join(project_path, "end_assumptions")

        if not os.path.isdir(start_dir) or not os.path.isdir(end_dir):
            print("[WARNING] Brak wymaganych katalogów — pomijam.")
            continue

        try:
            text_project = read_all_files_from_dir(start_dir)
            if not text_project.strip():
                print(f"[WARNING] Brak danych wejściowych w {start_dir}")
                continue

            text_end = read_all_files_from_dir(end_dir)

            project_real_name = extract_project_name(text_project)
            objectives = extract_objectives(text_project, project_real_name)
            report = verify_objectives(objectives, text_end)

            with open(os.path.join(project_path, "objectives.json"), "w", encoding="utf-8") as f:
                json.dump(objectives, f, indent=2, ensure_ascii=False)

            with open(os.path.join(project_path, "raport.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            all_assumptions.extend(report)
            processed_count += 1

        except Exception as e:
            msg = f"Błąd w projekcie {project_name}: {e}"
            print(f"[ERROR] {msg}")
            errors.append(msg)

    if all_assumptions:
        load_assumptions_to_neo4j(all_assumptions)

    return {
        "status": "success",
        "processed_projects": processed_count,
        "errors": errors
    }


if __name__ == "__main__":
    analyze_assumptions()

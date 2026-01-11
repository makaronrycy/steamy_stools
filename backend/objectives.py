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

def main():
    for project_name in os.listdir(BASE_PROJECTS_DIR):
        project_path = os.path.join(BASE_PROJECTS_DIR, project_name)

        if not os.path.isdir(project_path):
            continue

        print(f"\n=== Projekt: {project_name} ===")

        start_dir = os.path.join(project_path, "start_assumptions")
        end_dir = os.path.join(project_path, "end_assumptions")

        if not os.path.isdir(start_dir) or not os.path.isdir(end_dir):
            print(" Brak wymaganych folderów – pomijam")
            continue

        text_project = read_all_files_from_dir(start_dir)
        text_end = read_all_files_from_dir(end_dir)

        
        project_name = extract_project_name(text_project)
        

        
        objectives = extract_objectives(text_project, project_name)

        with open(os.path.join(project_path, "objectives.json"), "w", encoding="utf-8") as f:
            json.dump(objectives, f, indent=2, ensure_ascii=False)

        
        raport = verify_objectives(objectives, text_end)

        with open(os.path.join(project_path, "raport.json"), "w", encoding="utf-8") as f:
            json.dump(raport, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()

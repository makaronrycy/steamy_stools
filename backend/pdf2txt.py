import pymupdf
import pymupdf4llm
from pathlib import Path
import os

def extract_text_from_file(file_path: str) -> str:
    """
    Przyjmuje ścieżkę do PDF i ZWRACA tekst (Markdown).
    Obecnie wspiera tylko PDF (bez konwersji DOC/PPT na Linuxie).
    """
    input_path = Path(file_path).resolve()
    ext = input_path.suffix.lower()

    if ext != ".pdf":
         # Fallback for text files
        if ext in [".txt", ".md", ".json"]:
             with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
                 return f.read()
                 
        return f"[WARNING] Format {ext} nie jest wspierany w wersji Docker (Linux). Proszę przekonwertować na PDF."

    try:
        doc = pymupdf.open(input_path)
        text = pymupdf4llm.to_markdown(doc)
        return text
    except Exception as e:
        return f"Błąd ekstrakcji PDF: {str(e)}"

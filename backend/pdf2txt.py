#!/usr/bin/env python3
"""
pdf2txt.py

Moduł pomocniczy do ekstrakcji tekstu z plików dokumentów.

Obecnie wspierane formaty:
- PDF (pełna ekstrakcja do Markdown przy użyciu PyMuPDF + pymupdf4llm)
- TXT / MD / JSON (fallback – bez konwersji)

Moduł jest przystosowany do pracy w środowisku Linux / Docker,
gdzie nie są dostępne natywne konwertery DOC/PPT.
"""

from pathlib import Path

import pymupdf
import pymupdf4llm


def extract_text_from_file(file_path: str) -> str:
    """
    Ekstrahuje tekst z pliku dokumentu.

    W przypadku plików PDF wykonywana jest konwersja do Markdown
    przy użyciu PyMuPDF i pymupdf4llm.

    Dla prostych plików tekstowych (.txt, .md, .json) wykonywany
    jest bezpośredni odczyt zawartości.

    Pozostałe formaty nie są obsługiwane w środowisku Linux/Docker
    i zwracany jest komunikat ostrzegawczy.

    Parameters
    ----------
    file_path : str
        Ścieżka do pliku wejściowego.

    Returns
    -------
    str
        Wyekstrahowany tekst dokumentu lub komunikat ostrzegawczy
        w przypadku nieobsługiwanego formatu.
    """
    input_path = Path(file_path).resolve()
    extension = input_path.suffix.lower()

    # Fallback for plain text files
    if extension in {".txt", ".md", ".json"}:
        try:
            with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            return f"[ERROR] Nie udało się odczytać pliku tekstowego: {e}"

    # PDF processing
    if extension == ".pdf":
        try:
            doc = pymupdf.open(input_path)
            text = pymupdf4llm.to_markdown(doc)
            return text
        except Exception as e:
            return f"[ERROR] Błąd ekstrakcji PDF: {e}"

    return (
        f"[WARNING] Format '{extension}' nie jest wspierany w wersji Linux/Docker. "
        "Proszę przekonwertować dokument do formatu PDF."
    )

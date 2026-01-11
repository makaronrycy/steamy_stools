import pymupdf
import pymupdf4llm
import comtypes.client
from pathlib import Path
import tempfile


def convert_to_pdf_temp(input_path: Path) -> Path:
    """
    Konwertuje DOC/DOCX/PPT/PPTX do PDF w katalogu tymczasowym
    """
    input_path = input_path.resolve()
    temp_dir = Path(tempfile.mkdtemp())
    output_pdf = temp_dir / (input_path.stem + ".pdf")

    ext = input_path.suffix.lower()

    if ext in [".doc", ".docx"]:
        word = comtypes.client.CreateObject("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(input_path))
        doc.SaveAs(str(output_pdf), FileFormat=17)  # PDF
        doc.Close()
        word.Quit()

    elif ext in [".ppt", ".pptx"]:
        powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
        powerpoint.Visible = 1
        presentation = powerpoint.Presentations.Open(str(input_path), WithWindow=False)
        presentation.SaveAs(str(output_pdf), FileFormat=32)  # PDF
        presentation.Close()
        powerpoint.Quit()

    else:
        raise ValueError("Nieobsługiwany typ pliku.")

    return output_pdf


def extract_text_from_file(file_path: str) -> str:
    """
    Przyjmuje ścieżkę do PDF/DOCX/PPTX i ZWRACA tekst (bez zapisu)
    """
    input_path = Path(file_path).resolve()
    ext = input_path.suffix.lower()

    if ext == ".pdf":
        pdf_path = input_path
    elif ext in [".doc", ".docx", ".ppt", ".pptx"]:
        pdf_path = convert_to_pdf_temp(input_path)
    else:
        raise ValueError(f"Nieobsługiwany typ pliku: {ext}")

    doc = pymupdf.open(pdf_path)
    text = pymupdf4llm.to_markdown(doc)

    return text

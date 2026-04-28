"""
PDF Parser utility using PyMuPDF (fitz).
Extracts raw text from PDF files with page tracking.
"""

import fitz  # PyMuPDF


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors."""

    pass


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract full text from a PDF file.

    Raises:
        PDFExtractionError: If the PDF is corrupted, empty, or cannot be read.
    """
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
    except Exception as e:
        raise PDFExtractionError(f"Impossible d'ouvrir le PDF: {str(e)}")

    if len(doc) == 0:
        doc.close()
        raise PDFExtractionError("Le PDF est vide (aucune page).")

    full_text = []
    for page_num in range(len(doc)):
        try:
            page = doc.load_page(page_num)
            text = page.get_text("text")
            if text.strip():
                full_text.append(f"--- PAGE {page_num + 1} ---\n{text}")
        except Exception as e:
            raise PDFExtractionError(
                f"Erreur lors de l'extraction de la page {page_num + 1}: {str(e)}"
            )

    doc.close()

    if not full_text:
        raise PDFExtractionError(
            "Le PDF ne contient aucun texte extractible (scanné ou image uniquement)."
        )

    return "\n\n".join(full_text)


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """
    Extract text from a Streamlit uploaded file object.

    Raises:
        PDFExtractionError: If extraction fails.
    """
    try:
        pdf_bytes = uploaded_file.read()
    except Exception as e:
        raise PDFExtractionError(f"Impossible de lire le fichier: {str(e)}")

    if len(pdf_bytes) == 0:
        raise PDFExtractionError("Le fichier est vide.")

    uploaded_file.seek(0)  # Reset for potential re-read
    return extract_text_from_pdf(pdf_bytes)


def get_page_count(pdf_content: bytes) -> int:
    """Get the number of pages in a PDF."""
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0

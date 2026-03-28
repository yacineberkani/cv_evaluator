"""
PDF Parser utility using PyMuPDF (fitz).
Extracts raw text from PDF files with page tracking.
"""

import fitz  # PyMuPDF
import io
from typing import Optional


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract full text from a PDF file."""
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    full_text = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        if text.strip():
            full_text.append(f"--- PAGE {page_num + 1} ---\n{text}")
    doc.close()
    return "\n\n".join(full_text)


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """Extract text from a Streamlit uploaded file object."""
    pdf_bytes = uploaded_file.read()
    uploaded_file.seek(0)  # Reset for potential re-read
    return extract_text_from_pdf(pdf_bytes)


def get_page_count(pdf_content: bytes) -> int:
    """Get the number of pages in a PDF."""
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    count = len(doc)
    doc.close()
    return count

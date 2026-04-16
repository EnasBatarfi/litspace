# This module provides functionality to parse PDF files and extract text content from each page.

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


def parse_pdf_to_pages(pdf_path: str | Path) -> dict:
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages: list[dict] = []

    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)

        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append(
                {
                    "page_number": page_index,
                    "text": text.strip(),
                }
            )

    return {
        "total_pages": total_pages,
        "pages": pages,
    }
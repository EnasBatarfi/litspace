# This module provides functions for handling file storage related to project uploads.
# It includes functionality to ensure unique filenames, save uploaded PDF files, and manage project directories.

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.utils.paths import ensure_project_directories, get_project_raw_dir
from app.utils.slug import slugify


def build_unique_pdf_name(original_filename: str, project_slug: str) -> str:
    original_name = Path(original_filename).name
    suffix = Path(original_name).suffix.lower()

    if suffix != ".pdf":
        raise ValueError("Only PDF files are supported.")

    safe_stem = slugify(Path(original_name).stem) or "paper"
    candidate = f"{safe_stem}{suffix}"

    project_raw_dir = get_project_raw_dir(project_slug)
    destination = project_raw_dir / candidate

    counter = 2
    while destination.exists():
        candidate = f"{safe_stem}-{counter}{suffix}"
        destination = project_raw_dir / candidate
        counter += 1

    return candidate


def save_uploaded_pdf(file: UploadFile, project_slug: str) -> dict[str, str]:
    if not file.filename:
        raise ValueError("Uploaded file must have a filename.")

    ensure_project_directories(project_slug)

    original_filename = Path(file.filename).name
    stored_filename = build_unique_pdf_name(original_filename, project_slug)

    project_raw_dir = get_project_raw_dir(project_slug)
    destination = project_raw_dir / stored_filename

    with destination.open("wb") as out_file:
        while chunk := file.file.read(1024 * 1024):
            out_file.write(chunk)

    relative_path = Path("data") / "raw" / project_slug / stored_filename

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "absolute_path": str(destination),
        "relative_path": str(relative_path),
    }
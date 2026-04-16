# This module defines API routes for parsing papers in the application.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.paper import Paper
from app.models.project import Project
from app.schemas.paper import PaperRead
from app.services.parsing.document_store import save_processed_document
from app.services.parsing.pdf_parser import parse_pdf_to_pages
from app.utils.paths import (
    get_processed_document_path,
    resolve_repo_relative_path,
    to_repo_relative_path,
)

router = APIRouter(prefix="/papers", tags=["parsing"])


@router.post("/{paper_id}/parse", response_model=PaperRead)
def parse_paper(
    paper_id: int,
    db: Session = Depends(get_db),
) -> Paper:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {paper_id} not found",
        )

    project = db.get(Project, paper.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {paper.project_id} not found for paper {paper_id}",
        )

    source_pdf_path = resolve_repo_relative_path(paper.file_path)
    if not source_pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Source PDF is missing on disk: {paper.file_path}",
        )

    try:
        parsed = parse_pdf_to_pages(source_pdf_path)
    except Exception as exc:
        paper.status = "failed"
        db.add(paper)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse PDF: {exc}",
        ) from exc

    processed_path = get_processed_document_path(project.slug, paper.id)

    payload = {
        "paper_id": paper.id,
        "project_id": project.id,
        "project_slug": project.slug,
        "original_filename": paper.original_filename,
        "stored_filename": paper.stored_filename,
        "source_pdf_path": paper.file_path,
        "total_pages": parsed["total_pages"],
        "pages": parsed["pages"],
    }

    save_processed_document(processed_path, payload)

    paper.processed_path = to_repo_relative_path(processed_path)
    paper.status = "parsed"

    db.add(paper)
    db.commit()
    db.refresh(paper)

    return paper
# This module defines the API route for chunking a processed paper document.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.paper import Paper
from app.models.project import Project
from app.schemas.paper import PaperRead
from app.services.chunking.chunker import chunk_processed_document
from app.services.parsing.document_store import load_processed_document, save_processed_document
from app.utils.paths import (
    get_chunk_document_path,
    resolve_repo_relative_path,
)

router = APIRouter(prefix="/papers", tags=["chunking"])


@router.post("/{paper_id}/chunk", response_model=PaperRead)
def chunk_paper(
    paper_id: int,
    db: Session = Depends(get_db),
) -> Paper:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {paper_id} not found",
        )

    if not paper.processed_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paper {paper_id} has not been parsed yet",
        )

    project = db.get(Project, paper.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {paper.project_id} not found for paper {paper_id}",
        )

    processed_path = resolve_repo_relative_path(paper.processed_path)
    if not processed_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processed document is missing on disk: {paper.processed_path}",
        )

    try:
        processed_doc = load_processed_document(processed_path)
        processed_doc["source_processed_path"] = paper.processed_path

        chunk_doc = chunk_processed_document(
            processed_doc=processed_doc,
            min_chunk_tokens=450,
            max_chunk_tokens=650,
            overlap_tokens=100,
        )
    except Exception as exc:
        paper.status = "failed"
        db.add(paper)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to chunk document: {exc}",
        ) from exc

    chunk_output_path = get_chunk_document_path(project.slug, paper.id)
    save_processed_document(chunk_output_path, chunk_doc)

    paper.status = "chunked"
    db.add(paper)
    db.commit()
    db.refresh(paper)

    return paper
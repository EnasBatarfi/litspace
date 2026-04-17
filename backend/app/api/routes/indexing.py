
# This module defines the API endpoint for indexing a project's papers into both a vector index (Chroma) and a BM25 index.

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.paper import Paper
from app.models.project import Project
from app.schemas.indexing import ProjectIndexResponse
from app.services.embedding.encoder import embed_texts
from app.services.indexing.bm25_indexer import build_bm25_payload, save_bm25_payload
from app.services.indexing.chroma_indexer import (
    add_chunk_records_to_collection,
    get_collection_name,
    recreate_project_collection,
)
from app.services.parsing.document_store import load_processed_document
from app.utils.paths import (
    get_chunk_document_path,
    get_project_bm25_path,
    to_repo_relative_path,
)

router = APIRouter(prefix="/projects", tags=["indexing"])


@router.post("/{project_id}/index", response_model=ProjectIndexResponse)
def index_project(
    project_id: int,
    db: Session = Depends(get_db),
) -> ProjectIndexResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    papers = db.scalars(
        select(Paper)
        .where(Paper.project_id == project_id)
        .order_by(Paper.id.asc())
    ).all()

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project {project_id} has no papers to index",
        )

    chunk_records: list[dict] = []
    indexed_paper_ids: list[int] = []

    for paper in papers:
        if paper.status not in {"chunked", "indexed"}:
            continue

        chunk_path = get_chunk_document_path(project.slug, paper.id)
        if not chunk_path.exists():
            continue

        chunk_doc = load_processed_document(chunk_path)
        chunks = chunk_doc.get("chunks", [])
        if not chunks:
            continue

        paper_title = paper.title or Path(paper.original_filename).stem

        for chunk in chunks:
            chunk_records.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"],
                    "paper_id": chunk["paper_id"],
                    "project_id": chunk["project_id"],
                    "project_slug": chunk["project_slug"],
                    "page_start": chunk["page_start"],
                    "page_end": chunk["page_end"],
                    "section_heading": chunk.get("section_heading"),
                    "text": chunk["text"],
                    "paper_title": paper_title,
                    "original_filename": paper.original_filename,
                }
            )

        indexed_paper_ids.append(paper.id)

    if not chunk_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project {project_id} has no chunked papers ready for indexing",
        )

    try:
        embeddings = embed_texts(
            [record["text"] for record in chunk_records],
            batch_size=16,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build embeddings: {exc}",
        ) from exc

    try:
        collection = recreate_project_collection(project.slug)
        add_chunk_records_to_collection(collection, chunk_records, embeddings)

        bm25_payload = build_bm25_payload(
            project_id=project.id,
            project_slug=project.slug,
            records=chunk_records,
        )
        bm25_path = get_project_bm25_path(project.slug)
        save_bm25_payload(bm25_path, bm25_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build project indexes: {exc}",
        ) from exc

    indexed_paper_id_set = set(indexed_paper_ids)
    for paper in papers:
        if paper.id in indexed_paper_id_set:
            paper.status = "indexed"
            db.add(paper)

    db.commit()

    return ProjectIndexResponse(
        project_id=project.id,
        project_slug=project.slug,
        total_project_papers=len(papers),
        total_indexed_papers=len(indexed_paper_ids),
        indexed_paper_ids=indexed_paper_ids,
        total_chunks_indexed=len(chunk_records),
        embedding_model=settings.embedding_model,
        chroma_collection=get_collection_name(project.slug),
        bm25_index_path=to_repo_relative_path(get_project_bm25_path(project.slug)),
    )
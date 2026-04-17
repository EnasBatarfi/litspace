# This file defines the API endpoint for retrieving evidence from a project based on a query.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalHit
from app.services.retrieval.bm25_retriever import lexical_retrieve
from app.services.retrieval.chroma_retriever import semantic_retrieve
from app.services.retrieval.hybrid import reciprocal_rank_fusion

router = APIRouter(prefix="/projects", tags=["retrieval"])


@router.post("/{project_id}/retrieve", response_model=RetrievalResponse)
def retrieve_project_evidence(
    project_id: int,
    request: RetrievalRequest,
    db: Session = Depends(get_db),
) -> RetrievalResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    try:
        semantic_hits = semantic_retrieve(
            project_slug=project.slug,
            query=request.query,
            top_k=max(request.top_k, 10),
        )
        lexical_hits = lexical_retrieve(
            project_slug=project.slug,
            query=request.query,
            top_k=max(request.top_k, 10),
        )
        merged_hits = reciprocal_rank_fusion(
            semantic_hits=semantic_hits,
            lexical_hits=lexical_hits,
            top_k=request.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {exc}",
        ) from exc

    return RetrievalResponse(
        project_id=project.id,
        project_slug=project.slug,
        query=request.query,
        top_k=request.top_k,
        total_hits=len(merged_hits),
        hits=[RetrievalHit(**hit) for hit in merged_hits],
    )
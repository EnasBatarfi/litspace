# This file defines the API endpoint for retrieving evidence based on a query for a specific project.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalHit
from app.services.retrieval.pipeline import hybrid_retrieve

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
        merged_hits = hybrid_retrieve(
            project_slug=project.slug,
            query=request.query,
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
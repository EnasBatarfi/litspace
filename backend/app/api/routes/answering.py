# This module defines API routes for answering questions related to projects. It includes an endpoint for asking a question about a specific project and receiving an answer based on the project's data and context. The endpoint validates the project ID, processes the question using the answering service, and returns the answer along with relevant metadata about the sources used in generating the answer.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.project import Project
from app.schemas.answering import AskRequest, AskResponse, AnswerSource
from app.services.answering.answerer import ask_project

router = APIRouter(prefix="/projects", tags=["answering"])


@router.post("/{project_id}/ask", response_model=AskResponse)
def ask_project_question(
    project_id: int,
    request: AskRequest,
    db: Session = Depends(get_db),
) -> AskResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    try:
        result = ask_project(
            project_id=project.id,
            project_slug=project.slug,
            query=request.query,
            top_k=request.top_k or settings.default_answer_top_k,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {exc}",
        ) from exc

    return AskResponse(
        project_id=result["project_id"],
        project_slug=result["project_slug"],
        query=result["query"],
        answer=result["answer"],
        insufficient_evidence=result["insufficient_evidence"],
        retrieval_hits_count=result["retrieval_hits_count"],
        used_sources=[AnswerSource(**src) for src in result["used_sources"]],
    )
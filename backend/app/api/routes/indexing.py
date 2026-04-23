
# This module defines the API endpoint for indexing a project's papers into both a vector index (Chroma) and a BM25 index.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.project import Project
from app.schemas.indexing import ProjectIndexResponse
from app.services.indexing.project_index_manager import sync_project_indexes

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

    try:
        sync_result = sync_project_indexes(project, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build project indexes: {exc}",
        ) from exc

    if sync_result["total_project_papers"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project {project_id} has no papers to index",
        )

    if sync_result["total_chunks_indexed"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project {project_id} has no chunked papers ready for indexing",
        )

    return ProjectIndexResponse(
        project_id=project.id,
        project_slug=project.slug,
        total_project_papers=sync_result["total_project_papers"],
        total_indexed_papers=sync_result["total_indexed_papers"],
        indexed_paper_ids=sync_result["indexed_paper_ids"],
        total_chunks_indexed=sync_result["total_chunks_indexed"],
        embedding_model=settings.embedding_model,
        chroma_collection=sync_result["chroma_collection"],
        bm25_index_path=sync_result["bm25_index_path"],
    )

# This file is focused on the upload endpoint, which is the first step in the paper processing pipeline. It handles:
# - Validating the uploaded file (checking filename, extension, and content type)
# - Saving the file to storage using the `save_uploaded_pdf` service function
# - Creating a new Paper record in the database with the initial status of "uploaded"

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.paper import Paper
from app.models.project import Project
from app.schemas.paper import PaperListItem, PaperRead
from app.services.indexing.project_index_manager import clear_project_indexes, sync_project_indexes
from app.services.storage import save_uploaded_pdf
from app.utils.paths import get_chunk_document_path, resolve_repo_relative_path

router = APIRouter(prefix="/projects", tags=["papers"])


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return project


@router.post(
    "/{project_id}/papers/upload",
    response_model=PaperRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_paper(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Paper:
    project = get_project_or_404(project_id, db)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    suffix = Path(file.filename).suffix.lower()
    if suffix != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF uploads are supported.",
        )

    allowed_content_types = {
        "application/pdf",
        "application/octet-stream",
        "",
        None,
    }
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unexpected content type: {file.content_type}",
        )

    try:
        saved = save_uploaded_pdf(file=file, project_slug=project.slug)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        file.file.close()

    paper = Paper(
        project_id=project.id,
        original_filename=saved["original_filename"],
        stored_filename=saved["stored_filename"],
        title=None,
        authors=None,
        year=None,
        status="uploaded",
        file_path=saved["relative_path"],
    )

    db.add(paper)
    db.commit()
    db.refresh(paper)

    return paper


@router.get(
    "/{project_id}/papers",
    response_model=list[PaperListItem],
)
def list_project_papers(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[Paper]:
    _ = get_project_or_404(project_id, db)

    papers = db.scalars(
        select(Paper)
        .where(Paper.project_id == project_id)
        .order_by(Paper.created_at.desc())
    ).all()

    return list(papers)


@router.delete(
    "/{project_id}/papers/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project_paper(
    project_id: int,
    paper_id: int,
    db: Session = Depends(get_db),
) -> None:
    project = get_project_or_404(project_id, db)
    paper = db.get(Paper, paper_id)
    if paper is None or paper.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {paper_id} not found in project {project_id}",
        )

    file_paths = [resolve_repo_relative_path(paper.file_path)]
    if paper.processed_path:
        file_paths.append(resolve_repo_relative_path(paper.processed_path))
    file_paths.append(get_chunk_document_path(project.slug, paper.id))

    db.delete(paper)
    db.commit()

    for file_path in file_paths:
        file_path.unlink(missing_ok=True)

    try:
        sync_project_indexes(project, db)
    except Exception:
        clear_project_indexes(project.slug)

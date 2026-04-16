# This is the API router for project-related endpoints. It includes endpoints for creating a new project, listing all projects, and retrieving a specific project by its ID. The router uses SQLAlchemy for database interactions and FastAPI for request handling and response modeling.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectListItem, ProjectRead
from app.utils.paths import ensure_project_directories
from app.utils.slug import slugify

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    base_slug = slugify(payload.name)
    slug = base_slug
    suffix = 2

    while db.scalar(select(Project).where(Project.slug == slug)) is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    project = Project(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        topic_label=payload.topic_label,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    ensure_project_directories(project.slug)

    return project


@router.get("", response_model=list[ProjectListItem])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    projects = db.scalars(
        select(Project).order_by(Project.created_at.desc())
    ).all()
    return list(projects)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return project
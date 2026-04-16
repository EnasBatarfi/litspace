# This module defines paths for the backend application, including directories for raw PDFs, processed data, and indices. It also provides utility functions to ensure that these directories exist and to retrieve project-specific paths.
# The paths are constructed based on the backend directory and settings defined in the configuration. The utility functions allow for easy management of project-specific directories, ensuring that the necessary structure is in place for storing data related to different projects.

from pathlib import Path

from app.core.config import settings


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = (BACKEND_DIR / settings.data_dir).resolve()
RAW_DIR = (BACKEND_DIR / settings.raw_pdf_dir).resolve()
PROCESSED_DIR = (BACKEND_DIR / settings.processed_dir).resolve()
INDEX_DIR = (BACKEND_DIR / settings.index_dir).resolve()
EVAL_DIR = (BACKEND_DIR / settings.eval_dir).resolve()


def ensure_base_data_directories() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)


def get_project_raw_dir(project_slug: str) -> Path:
    return RAW_DIR / project_slug


def get_project_processed_dir(project_slug: str) -> Path:
    return PROCESSED_DIR / project_slug


def get_project_index_dir(project_slug: str) -> Path:
    return INDEX_DIR / project_slug


def ensure_project_directories(project_slug: str) -> None:
    get_project_raw_dir(project_slug).mkdir(parents=True, exist_ok=True)
    get_project_processed_dir(project_slug).mkdir(parents=True, exist_ok=True)
    get_project_index_dir(project_slug).mkdir(parents=True, exist_ok=True)
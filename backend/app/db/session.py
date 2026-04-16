# This is a module for managing the database session in a FastAPI application using SQLAlchemy. 
# It sets up the database connection, creates a session factory, and provides a dependency function to get a database session for use in API endpoints.
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


BACKEND_DIR = Path(__file__).resolve().parents[2]
DB_PATH = (BACKEND_DIR / settings.sqlite_path).resolve()

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
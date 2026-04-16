# This is to define the Project model, which represents a project in the database. Each project can have multiple papers associated with it. The model includes fields for the project's name, slug, description, topic label, and creation timestamp. The relationship to the Paper model is defined to allow for easy access to the papers associated with each project.
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    papers: Mapped[list["Paper"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
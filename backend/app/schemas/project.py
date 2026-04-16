# This file defines Pydantic models for creating and reading project data in the application. The models include validation rules for the fields and are used for data transfer between the API and the database.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    topic_label: str | None = Field(default=None, max_length=100)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    topic_label: str | None
    created_at: datetime


class ProjectListItem(ProjectRead):
    pass
# This is a Pydantic model for representing a paper in the application. It includes fields for the paper's ID, project ID, original and stored filenames, title, authors, year, status, file path, and creation timestamp. The model is configured to allow population from ORM objects using the `from_attributes` option in the `ConfigDict`.

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaperRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    original_filename: str
    stored_filename: str
    title: str | None
    authors: str | None
    year: int | None
    status: str
    file_path: str
    created_at: datetime


class PaperListItem(PaperRead):
    pass
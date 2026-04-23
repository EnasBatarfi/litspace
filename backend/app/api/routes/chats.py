from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.chat import Chat
from app.models.project import Project
from app.schemas.chat import ChatCreate, ChatListItem, ChatRead

router = APIRouter(tags=["chats"])


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return project


def get_chat_or_404(chat_id: int, db: Session) -> Chat:
    chat = db.scalar(
        select(Chat)
        .where(Chat.id == chat_id)
        .options(selectinload(Chat.messages))
    )
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {chat_id} not found",
        )
    return chat


@router.post(
    "/projects/{project_id}/chats",
    response_model=ChatRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chat(
    project_id: int,
    payload: ChatCreate,
    db: Session = Depends(get_db),
) -> Chat:
    _ = get_project_or_404(project_id, db)

    title = (payload.title or "").strip() or "New chat"
    chat = Chat(project_id=project_id, title=title)
    db.add(chat)
    db.commit()

    return get_chat_or_404(chat.id, db)


@router.get("/projects/{project_id}/chats", response_model=list[ChatListItem])
def list_project_chats(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[ChatListItem]:
    _ = get_project_or_404(project_id, db)

    chats = db.scalars(
        select(Chat)
        .where(Chat.project_id == project_id)
        .options(selectinload(Chat.messages))
        .order_by(Chat.updated_at.desc(), Chat.created_at.desc())
    ).all()

    return [
        ChatListItem(
            id=chat.id,
            project_id=chat.project_id,
            title=chat.title,
            message_count=len(chat.messages),
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )
        for chat in chats
    ]


@router.get("/chats/{chat_id}", response_model=ChatRead)
def get_chat(chat_id: int, db: Session = Depends(get_db)) -> Chat:
    return get_chat_or_404(chat_id, db)


@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: int, db: Session = Depends(get_db)) -> None:
    chat = get_chat_or_404(chat_id, db)
    db.delete(chat)
    db.commit()

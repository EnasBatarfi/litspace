# This module defines API routes for answering questions related to projects. It includes an endpoint for asking a question about a specific project and receiving an answer based on the project's data and context. The endpoint validates the project ID, processes the question using the answering service, and returns the answer along with relevant metadata about the sources used in generating the answer.

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.session import get_db
from app.models.chat import Chat
from app.models.message import Message
from app.models.paper import Paper
from app.models.project import Project
from app.schemas.answering import AskRequest, AskResponse, AnswerSource, AnswerTiming, AnswerUsage
from app.services.answering.answerer import ask_project

router = APIRouter(prefix="/projects", tags=["answering"])


def build_chat_title(query: str) -> str:
    compact = " ".join(query.split()).strip()
    if len(compact) <= 56:
        return compact
    return f"{compact[:53]}..."


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

    chat: Chat | None = None
    if request.chat_id is not None:
        chat = db.scalar(
            select(Chat)
            .where(Chat.id == request.chat_id)
            .options(selectinload(Chat.messages))
        )
        if chat is None or chat.project_id != project.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat {request.chat_id} not found in project {project_id}",
            )

    try:
        project_papers = db.scalars(
            select(Paper)
            .where(Paper.project_id == project.id)
        ).all()

        result = ask_project(
            project_id=project.id,
            project_slug=project.slug,
            query=request.query,
            top_k=request.top_k or settings.default_answer_top_k,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
            project_papers=project_papers,
            recent_messages=chat.messages if chat is not None else [],
            selected_paper_ids=request.selected_paper_ids,
            paper_order_ids=request.paper_order_ids,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {exc}",
        ) from exc

    if chat is not None:
        is_first_user_turn = not any(message.role == "user" for message in chat.messages)

        db.add(
            Message(
                chat_id=chat.id,
                role="user",
                content=request.query,
                sources=[],
                insufficient_evidence=False,
                retrieval_hits_count=0,
            )
        )
        db.add(
            Message(
                chat_id=chat.id,
                role="assistant",
                content=result["answer"],
                sources=result["used_sources"],
                insufficient_evidence=result["insufficient_evidence"],
                retrieval_hits_count=result["retrieval_hits_count"],
            )
        )

        if is_first_user_turn or chat.title.strip().lower() == "new chat":
            chat.title = build_chat_title(request.query)

        chat.updated_at = dt.datetime.now(dt.UTC)
        db.add(chat)
        db.commit()

    return AskResponse(
        project_id=result["project_id"],
        project_slug=result["project_slug"],
        chat_id=chat.id if chat is not None else None,
        query=result["query"],
        answer=result["answer"],
        action=result.get("action"),
        insufficient_evidence=result["insufficient_evidence"],
        retrieval_hits_count=result["retrieval_hits_count"],
        used_sources=[AnswerSource(**src) for src in result["used_sources"]],
        timing=AnswerTiming(**result["timing"]) if result.get("timing") else None,
        usage=AnswerUsage(**result["usage"]) if result.get("usage") else None,
    )

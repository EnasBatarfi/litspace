from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.project import Project
from app.services.embedding.encoder import embed_texts
from app.services.indexing.bm25_indexer import build_bm25_payload, save_bm25_payload
from app.services.indexing.chroma_indexer import (
    add_chunk_records_to_collection,
    delete_project_collection,
    get_collection_name,
    recreate_project_collection,
)
from app.services.parsing.document_store import load_processed_document
from app.utils.paths import (
    get_chunk_document_path,
    get_project_bm25_path,
    to_repo_relative_path,
)


def clear_project_indexes(project_slug: str) -> None:
    delete_project_collection(project_slug)
    bm25_path = get_project_bm25_path(project_slug)
    bm25_path.unlink(missing_ok=True)


def sync_project_indexes(project: Project, db: Session) -> dict:
    papers = db.scalars(
        select(Paper)
        .where(Paper.project_id == project.id)
        .order_by(Paper.id.asc())
    ).all()

    chunk_records: list[dict] = []
    indexed_paper_ids: list[int] = []

    for paper in papers:
        if paper.status not in {"chunked", "indexed"}:
            continue

        chunk_path = get_chunk_document_path(project.slug, paper.id)
        if not chunk_path.exists():
            continue

        chunk_doc = load_processed_document(chunk_path)
        chunks = chunk_doc.get("chunks", [])
        if not chunks:
            continue

        paper_title = paper.title or Path(paper.original_filename).stem

        for chunk in chunks:
            chunk_records.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"],
                    "paper_id": chunk["paper_id"],
                    "project_id": chunk["project_id"],
                    "project_slug": chunk["project_slug"],
                    "page_start": chunk["page_start"],
                    "page_end": chunk["page_end"],
                    "section_heading": chunk.get("section_heading"),
                    "text": chunk["text"],
                    "paper_title": paper_title,
                    "original_filename": paper.original_filename,
                }
            )

        indexed_paper_ids.append(paper.id)

    if not chunk_records:
        clear_project_indexes(project.slug)
        for paper in papers:
            chunk_path = get_chunk_document_path(project.slug, paper.id)
            if paper.status == "indexed" and chunk_path.exists():
                paper.status = "chunked"
                db.add(paper)

        db.commit()

        return {
            "total_project_papers": len(papers),
            "total_indexed_papers": 0,
            "indexed_paper_ids": [],
            "total_chunks_indexed": 0,
            "chroma_collection": get_collection_name(project.slug),
            "bm25_index_path": to_repo_relative_path(get_project_bm25_path(project.slug)),
        }

    embeddings = embed_texts(
        [record["text"] for record in chunk_records],
        batch_size=16,
    )

    collection = recreate_project_collection(project.slug)
    add_chunk_records_to_collection(collection, chunk_records, embeddings)

    bm25_payload = build_bm25_payload(
        project_id=project.id,
        project_slug=project.slug,
        records=chunk_records,
    )
    bm25_path = get_project_bm25_path(project.slug)
    save_bm25_payload(bm25_path, bm25_payload)

    indexed_paper_id_set = set(indexed_paper_ids)
    for paper in papers:
        chunk_path = get_chunk_document_path(project.slug, paper.id)
        if paper.id in indexed_paper_id_set:
            paper.status = "indexed"
            db.add(paper)
            continue

        if paper.status == "indexed" and chunk_path.exists():
            paper.status = "chunked"
            db.add(paper)

    db.commit()

    return {
        "total_project_papers": len(papers),
        "total_indexed_papers": len(indexed_paper_ids),
        "indexed_paper_ids": indexed_paper_ids,
        "total_chunks_indexed": len(chunk_records),
        "chroma_collection": get_collection_name(project.slug),
        "bm25_index_path": to_repo_relative_path(bm25_path),
    }

# This module implements the core logic for answering a user query based on retrieved project sources.

from __future__ import annotations

import re

from app.services.generation.prompting import build_system_prompt, build_user_prompt
from app.services.llm.client import generate_answer_text
from app.services.retrieval.pipeline import hybrid_retrieve


SOURCE_TAG_RE = re.compile(r"\[S(\d+)\]")
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _excerpt(text: str, max_chars: int = 500) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def _has_sufficient_evidence(query: str, hits: list[dict]) -> bool:
    if not hits:
        return False

    query_tokens = _tokenize(query)
    if not query_tokens:
        return False

    # Ignore very weak query words
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "what", "how", "who",
        "does", "did", "do", "in", "on", "of", "for", "to", "and", "with"
    }
    query_tokens = {t for t in query_tokens if t not in stopwords and len(t) > 2}

    if not query_tokens:
        return False

    best_overlap = 0
    best_ratio = 0.0

    for hit in hits[:5]:
        text_tokens = _tokenize(hit["text"])
        overlap = len(query_tokens & text_tokens)
        ratio = overlap / len(query_tokens)

        best_overlap = max(best_overlap, overlap)
        best_ratio = max(best_ratio, ratio)

    # require at least some direct overlap with the retrieved evidence
    if best_overlap >= 2:
        return True

    if best_ratio >= 0.5:
        return True

    return False


def ask_project(
    project_id: int,
    project_slug: str,
    query: str,
    top_k: int,
    temperature: float,
    max_output_tokens: int,
) -> dict:
    hits = hybrid_retrieve(
        project_slug=project_slug,
        query=query,
        top_k=top_k,
    )

    if not hits:
        return {
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": "Insufficient evidence in the retrieved project sources to answer confidently.",
            "insufficient_evidence": True,
            "retrieval_hits_count": 0,
            "used_sources": [],
        }

    if not _has_sufficient_evidence(query, hits):
        return {
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": "Insufficient evidence in the retrieved project sources to answer confidently.",
            "insufficient_evidence": True,
            "retrieval_hits_count": len(hits),
            "used_sources": [],
        }

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(query=query, hits=hits)

    answer = generate_answer_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    normalized = answer.lower()
    insufficient = (
        "insufficient evidence" in normalized
        or "not enough evidence" in normalized
        or "the provided sources do not" in normalized
    )

    if insufficient:
        return {
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": "Insufficient evidence in the retrieved project sources to answer confidently.",
            "insufficient_evidence": True,
            "retrieval_hits_count": len(hits),
            "used_sources": [],
        }

    cited_source_numbers = {
        int(match.group(1))
        for match in SOURCE_TAG_RE.finditer(answer)
        if 1 <= int(match.group(1)) <= len(hits)
    }

    if not cited_source_numbers:
        cited_source_numbers = set(range(1, min(len(hits), 3) + 1))

    used_sources = []
    for idx in sorted(cited_source_numbers):
        hit = hits[idx - 1]
        used_sources.append(
            {
                "source_id": f"S{idx}",
                "chunk_id": hit["chunk_id"],
                "paper_id": hit["paper_id"],
                "section_heading": hit.get("section_heading"),
                "paper_title": hit.get("paper_title"),
                "original_filename": hit.get("original_filename"),
                "page_start": hit["page_start"],
                "page_end": hit["page_end"],
                "hybrid_score": hit["hybrid_score"],
                "excerpt": _excerpt(hit["text"]),
            }
        )

    return {
        "project_id": project_id,
        "project_slug": project_slug,
        "query": query,
        "answer": answer,
        "insufficient_evidence": insufficient,
        "retrieval_hits_count": len(hits),
        "used_sources": used_sources,
    }

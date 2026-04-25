# This module implements the core logic for answering a user query based on retrieved project sources.

from __future__ import annotations

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from app.models.message import Message
from app.models.paper import Paper
from app.services.generation.prompting import build_system_prompt, build_user_prompt
from app.services.llm.client import LLMGenerationResult, generate_answer
from app.services.retrieval.pipeline import hybrid_retrieve


HELP_RESPONSE_TEXTS = (
    "I can help with the uploaded papers in this project. Ask for a summary, comparison, explanation, or evidence grounded in the sources.",
    "I can help with these papers. You can ask about one paper, selected papers, all papers, or a claim you want checked against the project sources.",
    "Ask me to summarize, compare, explain, or verify something from the papers in this project, and I'll stay grounded in the uploaded sources.",
    "I can help with the project papers here. Try a paper summary, a comparison, or an evidence check tied to the uploaded sources.",
)
PAPER_CLARIFICATION_TEXT = (
    'Which paper do you mean? You can name it, use its visible number, or select it first.'
)
PAPERS_CLARIFICATION_TEXT = (
    'Which papers do you mean? You can name them, use their visible numbers, or select them first.'
)
SUMMARY_PAPER_CLARIFICATION_TEXT = "Which paper should I summarize?"
SUMMARY_PAPERS_CLARIFICATION_TEXT = "Which papers should I summarize?"
COMPARE_PAPERS_CLARIFICATION_TEXT = "Which papers should I compare?"
COMPARE_WITH_CLARIFICATION_TEXT = "What should I compare it with?"
DISCOVERY_CLARIFICATION_TEXT = "What should I look for across the papers?"
SELECTED_PAPER_CLARIFICATION_TEXT = (
    "Select one or more papers first, or name the paper you want me to use."
)
INSUFFICIENT_EVIDENCE_TEXT = "Insufficient evidence in the retrieved project sources to answer confidently."
SELECTED_SCOPE_INSUFFICIENT_TEXT = (
    "I couldn't find enough evidence in the selected papers to answer confidently."
)
OUT_OF_SCOPE_REFUSAL_TEXT = "I can't answer that from the uploaded project papers."

SOURCE_GROUP_RE = re.compile(r"\[((?:S\d+(?:\s*,\s*S\d+)*))\]")
SOURCE_TAG_RE = re.compile(r"\[S(\d+)\]")
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
GREETING_WORDS = ("hi", "hello", "hey", "good morning", "good afternoon", "good evening")
INTRO_PREFIXES = ("i am", "i m", "im", "my name", "i want", "i need", "i'm")
HELP_WORDS = ("help", "assist", "assistant", "understand", "walk me through", "guide me")
PROJECT_WORDS = ("paper", "papers", "project", "research", "uploaded", "these")
FOLLOW_UP_PREFIXES = ("and ", "but ", "now ", "then ", "also ", "what about", "how about")
SINGULAR_PAPER_REFERENCE_PHRASES = (" this paper ", " the paper ", " that paper ", " selected paper ")
PLURAL_PAPER_REFERENCE_PHRASES = (" selected papers ", " these papers ", " those papers ", " the papers ", " each paper ")
SINGULAR_PRONOUN_REFERENCE_PHRASES = (" its ", " it ")
PLURAL_PRONOUN_REFERENCE_PHRASES = (" their ", " they ", " them ")
TASK_INTENT_WORDS = ("summarize", "compare", "evidence", "claim", "explain")
PROJECT_SCOPE_CUE_WORDS = (
    "paper",
    "papers",
    "project",
    "projects",
    "source",
    "sources",
    "uploaded",
    "selected",
    "study",
    "studies",
)
PAPER_ANALYSIS_WORDS = {
    "abstract",
    "claim",
    "claims",
    "compare",
    "comparison",
    "contribution",
    "contributions",
    "evaluate",
    "evaluation",
    "evidence",
    "explain",
    "finding",
    "findings",
    "goal",
    "limitation",
    "limitations",
    "method",
    "methods",
    "paper",
    "papers",
    "project",
    "result",
    "results",
    "scope",
    "source",
    "sources",
    "summarize",
    "summary",
}
QUOTE_INTENT_PHRASES = (
    "exact sentence",
    "exact quote",
    "exact wording",
    "exact line",
    "pull the exact sentence",
    "quote",
    "quoted",
    "quotation",
    "verbatim",
)
QUOTE_QUERY_STOPWORDS = {
    "each",
    "exact",
    "extract",
    "from",
    "line",
    "lines",
    "pull",
    "quote",
    "quoted",
    "quotation",
    "sentence",
    "sentences",
    "show",
    "verbatim",
    "wording",
}
AFFIRMATIVE_CONTINUATIONS = {
    "do it",
    "do that",
    "go ahead",
    "ok",
    "ok do it",
    "okay",
    "okay do it",
    "please do",
    "sure",
    "sure do it",
    "yes",
    "yes do it",
    "yes please",
}
OFFER_ACTION_VERBS = ("compare", "extract", "find", "give", "list", "pull", "quote", "show", "summarize")
DISCOVERY_INTENT_TOKENS = {
    "cite",
    "cites",
    "cited",
    "contain",
    "contains",
    "containing",
    "discuss",
    "discussed",
    "discusses",
    "find",
    "finding",
    "include",
    "included",
    "includes",
    "mention",
    "mentioned",
    "mentions",
    "refer",
    "reference",
    "references",
    "refers",
    "search",
    "talk",
    "talks",
    "use",
    "used",
    "uses",
    "using",
}
DISCOVERY_SCOPE_TOKENS = {"paper", "papers", "project", "uploaded", "selected", "these", "those"}
DISCOVERY_QUERY_STOPWORDS = {
    "about",
    "across",
    "all",
    "an",
    "and",
    "any",
    "can",
    "do",
    "does",
    "exactly",
    "find",
    "for",
    "help",
    "in",
    "is",
    "look",
    "me",
    "mention",
    "mentioned",
    "mentions",
    "of",
    "paper",
    "papers",
    "project",
    "search",
    "selected",
    "tell",
    "the",
    "these",
    "those",
    "u",
    "uploaded",
    "what",
    "which",
    "with",
    "you",
}
CLARIFICATION_REPLY_FILLER_WORDS = {
    "a",
    "all",
    "an",
    "and",
    "or",
    "paper",
    "papers",
    "please",
    "selected",
    "the",
    "them",
    "these",
    "those",
    "vs",
    "versus",
    "with",
}
FULL_INSUFFICIENT_ANSWER_PREFIXES = (
    "insufficient evidence in the provided sources",
    "insufficient evidence in the retrieved project sources",
    "i couldn t find enough evidence in the selected papers",
    "not enough evidence in the provided sources",
)
LOW_VALUE_UNSUPPORTED_PREFIXES = (
    "insufficient evidence in the provided sources",
    "insufficient evidence in the retrieved project sources",
    "i couldn t find enough evidence",
    "unsupported",
    "what is unsupported",
)
EXPLICIT_ALL_PHRASES = (
    "all papers",
    "all the papers",
    "all papers in this project",
    "all indexed papers",
    "across all papers",
)
ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
GENERIC_QUERY_WORDS = {
    "a",
    "about",
    "all",
    "an",
    "and",
    "answer",
    "compare",
    "evidence",
    "explain",
    "find",
    "first",
    "for",
    "from",
    "give",
    "in",
    "limitation",
    "method",
    "objective",
    "of",
    "paper",
    "papers",
    "results",
    "second",
    "selected",
    "summarize",
    "tell",
    "the",
    "their",
    "these",
    "this",
    "what",
    "which",
}
GENERIC_QUERY_WORDS |= set(ORDINAL_WORDS)
MAX_RECENT_MESSAGES = 6
MAX_RECENT_CHARS = 1400


@dataclass(frozen=True)
class PaperReference:
    id: int
    order: int
    label: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class ScopeResolution:
    paper_ids: list[int] | None
    target_labels: list[str]
    scope_source: str
    recent_history: list[dict[str, str]]
    resolved_query: str
    retrieval_query: str
    request_type: str
    reference_kind: str | None = None
    assistant_response: str | None = None
    assistant_action: str | None = None
    clarification_text: str | None = None


@dataclass(frozen=True)
class RecentTargets:
    single_ids: list[int]
    multi_ids: list[int]


@dataclass(frozen=True)
class PendingClarification:
    query: str
    request_type: str
    reference_kind: str | None


@dataclass(frozen=True)
class PendingAssistantOffer:
    action_query: str
    context_query: str


@dataclass(frozen=True)
class AnswerPlan:
    request_type: str
    response_mode: str
    organize_by: str
    prefer_table: bool = False


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[_/:-]+", " ", lowered)
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return " ".join(lowered.split())


def _compact_text(text: str, max_chars: int = 320) -> str:
    compact = " ".join(text.split()).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _excerpt(text: str, max_chars: int = 500) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def _normalize_citation_groups(answer: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        source_ids = [source_id.strip() for source_id in match.group(1).split(",")]
        return " ".join(f"[{source_id}]" for source_id in source_ids)

    return SOURCE_GROUP_RE.sub(replacer, answer)


def _extract_cited_source_numbers(answer: str, max_hits: int) -> set[int]:
    return {
        int(match.group(1))
        for match in SOURCE_TAG_RE.finditer(answer)
        if 1 <= int(match.group(1)) <= max_hits
    }


def _dedupe_preserving_order(values: Sequence[int]) -> list[int]:
    seen: set[int] = set()
    deduped: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _merge_hits(hits: Sequence[dict], top_k: int) -> list[dict]:
    merged: dict[str, dict] = {}
    for hit in hits:
        chunk_id = hit["chunk_id"]
        existing = merged.get(chunk_id)
        if existing is None or hit.get("hybrid_score", 0.0) > existing.get("hybrid_score", 0.0):
            merged[chunk_id] = {**hit}

    ranked = sorted(
        merged.values(),
        key=lambda hit: hit.get("hybrid_score", 0.0),
        reverse=True,
    )
    return ranked[:top_k]


def _message_sort_key(message: Message) -> tuple[str, int]:
    created_at = getattr(message, "created_at", None)
    return (created_at.isoformat() if created_at is not None else "", getattr(message, "id", 0))


def _help_response_for(query: str) -> str:
    normalized = _normalize_text(query)
    if not normalized:
        return HELP_RESPONSE_TEXTS[0]
    index = sum(ord(char) for char in normalized) % len(HELP_RESPONSE_TEXTS)
    return HELP_RESPONSE_TEXTS[index]


def _paper_label(paper: Paper) -> str:
    return (paper.title or Path(paper.original_filename).stem).strip()


def _paper_aliases(paper: Paper) -> tuple[str, ...]:
    raw_aliases = {
        _paper_label(paper),
        paper.original_filename,
        Path(paper.original_filename).stem,
    }
    aliases: set[str] = set()

    for raw in raw_aliases:
        normalized = _normalize_text(raw)
        if not normalized:
            continue
        aliases.add(normalized)

        stripped = re.sub(r"^\d+\s+", "", normalized).strip()
        if stripped:
            aliases.add(stripped)
            meaningful_tokens = [
                token
                for token in stripped.split()
                if token not in TITLE_STOPWORDS and token not in GENERIC_QUERY_WORDS
            ]
            for size in range(1, min(3, len(meaningful_tokens)) + 1):
                prefix = " ".join(meaningful_tokens[:size]).strip()
                if prefix and len(prefix) >= 3:
                    aliases.add(prefix)
            if 2 <= len(meaningful_tokens) <= 8:
                acronym = "".join(token[0] for token in meaningful_tokens)
                if len(acronym) >= 3:
                    aliases.add(acronym)

        for match in re.findall(r"\(([^)]+)\)", raw):
            normalized_match = _normalize_text(match)
            if normalized_match:
                aliases.add(normalized_match)

    return tuple(sorted(aliases, key=len, reverse=True))


def _build_paper_refs(
    project_papers: Sequence[Paper],
    paper_order_ids: Sequence[int],
) -> list[PaperReference]:
    paper_by_id = {paper.id: paper for paper in project_papers}
    ordered_papers: list[Paper] = []
    seen_ids: set[int] = set()

    for paper_id in paper_order_ids:
        paper = paper_by_id.get(paper_id)
        if paper is None or paper_id in seen_ids:
            continue
        ordered_papers.append(paper)
        seen_ids.add(paper_id)

    for paper in project_papers:
        if paper.id in seen_ids:
            continue
        ordered_papers.append(paper)
        seen_ids.add(paper.id)

    return [
        PaperReference(
            id=paper.id,
            order=index,
            label=_paper_label(paper),
            aliases=_paper_aliases(paper),
        )
        for index, paper in enumerate(ordered_papers, start=1)
    ]


def _build_recent_history(messages: Sequence[Message]) -> list[dict[str, str]]:
    ordered_messages = sorted(
        messages,
        key=_message_sort_key,
    )
    history: list[dict[str, str]] = []
    total_chars = 0

    for message in reversed(ordered_messages):
        content = _compact_text(message.content)
        if not content:
            continue
        history.append({"role": message.role, "content": content})
        total_chars += len(content)
        if len(history) >= MAX_RECENT_MESSAGES or total_chars >= MAX_RECENT_CHARS:
            break

    return list(reversed(history))


def _classify_request(query: str) -> str:
    normalized = _normalize_text(query)
    if "summar" in normalized or "explain" in normalized or "overview" in normalized:
        return "summary"
    if any(token in normalized for token in ("compare", "comparison", "vs", "versus")):
        return "compare"
    if any(token in normalized for token in ("evidence", "claim", "support", "supported")):
        return "evidence"
    return "question"


def _strip_leading_greeting(normalized: str) -> str:
    stripped = normalized.strip()
    for greeting in GREETING_WORDS:
        if stripped == greeting:
            return ""
        if stripped.startswith(f"{greeting} "):
            return stripped[len(greeting):].strip()
    return stripped


def _starts_with_factual_prompt(normalized: str) -> bool:
    return normalized.startswith(("what ", "which ", "how ", "why ", "who ", "where ", "when "))


def _has_quote_intent(query: str) -> bool:
    normalized = f" {_normalize_text(query)} "
    return any(f" {phrase} " in normalized for phrase in QUOTE_INTENT_PHRASES)


def _is_affirmative_continuation(query: str) -> bool:
    normalized = _normalize_text(query)
    return normalized in AFFIRMATIVE_CONTINUATIONS


def _discovery_query_tokens(query: str) -> set[str]:
    return _tokenize(_normalize_text(query))


def _has_discovery_intent(query: str) -> bool:
    tokens = _discovery_query_tokens(query)
    return bool(tokens & DISCOVERY_INTENT_TOKENS)


def _discovery_target_fragment(query: str) -> str:
    normalized = _normalize_text(query)
    tokens = [
        token
        for token in normalized.split()
        if token not in DISCOVERY_QUERY_STOPWORDS and token not in DISCOVERY_INTENT_TOKENS
    ]
    return " ".join(tokens)


def _looks_like_cross_paper_discovery_query(query: str, request_type: str) -> bool:
    if request_type != "question":
        return False

    normalized = _normalize_text(query)
    tokens = _discovery_query_tokens(query)
    if not tokens & DISCOVERY_INTENT_TOKENS:
        return False

    if "which paper" in normalized or "which papers" in normalized:
        return True

    return bool(tokens & DISCOVERY_SCOPE_TOKENS)


def _looks_like_identification_query(query: str, request_type: str) -> bool:
    if request_type != "question":
        return False

    normalized = _normalize_text(query)
    if not (
        normalized.startswith("which paper ")
        or normalized.startswith("which papers ")
        or normalized.startswith("among the selected papers which ")
        or normalized.startswith("among selected papers which ")
    ):
        return False

    return bool(_query_topic_fragment(query))


def _query_topic_fragment(query: str) -> str:
    normalized = _normalize_text(query)
    tokens = [
        token
        for token in normalized.split()
        if token not in GENERIC_QUERY_WORDS
        and token not in DISCOVERY_QUERY_STOPWORDS
        and token not in DISCOVERY_INTENT_TOKENS
        and token not in QUOTE_QUERY_STOPWORDS
        and token not in AFFIRMATIVE_CONTINUATIONS
    ]
    return " ".join(tokens)


def _is_project_help_request(query: str, explicit_target_ids: Sequence[int] | None = None) -> bool:
    normalized = _normalize_text(query)
    if not normalized or explicit_target_ids:
        return False

    if any(token in normalized for token in TASK_INTENT_WORDS):
        return False
    if _looks_like_cross_paper_discovery_query(query, "question"):
        return False

    remainder = _strip_leading_greeting(normalized)
    asks_for_capabilities = (
        any(word in remainder for word in HELP_WORDS)
        or any(phrase in remainder for phrase in ("what can i ask", "what kinds of questions", "can you help"))
    )
    mentions_project = any(word in remainder for word in PROJECT_WORDS)
    conversational_opening = (
        any(normalized.startswith(word) for word in GREETING_WORDS)
        or any(remainder.startswith(prefix) for prefix in INTRO_PREFIXES)
    )
    factual_question = _starts_with_factual_prompt(remainder)

    if any(token in normalized for token in ("summarize", "compare", "evidence", "claim")):
        factual_question = False

    if factual_question:
        return False

    if asks_for_capabilities and (mentions_project or conversational_opening):
        return True

    if asks_for_capabilities and len(remainder.split()) <= 6:
        return True

    return conversational_opening and len(remainder.split()) <= 5


def _is_explicit_all(query: str) -> bool:
    normalized = _normalize_text(query)
    if normalized in {"all", "all papers", "all of them"}:
        return True
    return any(phrase in normalized for phrase in EXPLICIT_ALL_PHRASES)


def _resolve_numeric_targets(query: str, paper_refs: Sequence[PaperReference]) -> list[int]:
    normalized = _normalize_text(query)
    ids: list[int] = []

    if re.fullmatch(r"\d+(?:\s*(?:,|and)\s*\d+)*", normalized):
        for match in re.findall(r"\d+", normalized):
            number = int(match)
            if 1 <= number <= len(paper_refs):
                ids.append(paper_refs[number - 1].id)

    for match in re.finditer(r"\bpaper(?:s)?\s+((?:\d+\s*(?:,|and)?\s*)+)\b", normalized):
        for number_text in re.findall(r"\d+", match.group(1)):
            number = int(number_text)
            if 1 <= number <= len(paper_refs):
                ids.append(paper_refs[number - 1].id)

    for match in re.finditer(r"\b(" + "|".join(ORDINAL_WORDS) + r")(?:\s+paper)?\b", normalized):
        number = ORDINAL_WORDS[match.group(1)]
        if 1 <= number <= len(paper_refs):
            ids.append(paper_refs[number - 1].id)

    for match in re.finditer(r"\b(\d+)(?:st|nd|rd|th)(?:\s+paper)?\b", normalized):
        number = int(match.group(1))
        if 1 <= number <= len(paper_refs):
            ids.append(paper_refs[number - 1].id)

    return _dedupe_preserving_order(ids)


def _query_name_fragment(query: str) -> str:
    normalized = _normalize_text(query)
    tokens = [token for token in normalized.split() if token not in GENERIC_QUERY_WORDS]
    return " ".join(tokens)


def _resolve_name_targets(query: str, paper_refs: Sequence[PaperReference]) -> list[int]:
    normalized = _normalize_text(query)
    fragment = _query_name_fragment(query)
    direct_matches: list[int] = []

    for paper_ref in paper_refs:
        for alias in paper_ref.aliases:
            if len(alias) < 3:
                continue
            if f" {alias} " in f" {normalized} " or (fragment and len(fragment) >= 3 and fragment in alias):
                direct_matches.append(paper_ref.id)
                break

    if direct_matches:
        return _dedupe_preserving_order(direct_matches)

    if not fragment or len(fragment.split()) > 8:
        return []

    ranked = sorted(
        ((paper_ref, max(SequenceMatcher(None, fragment, alias).ratio() for alias in paper_ref.aliases)) for paper_ref in paper_refs),
        key=lambda item: item[1],
        reverse=True,
    )
    if not ranked:
        return []

    best_ref, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if best_score >= 0.78 and best_score - second_score >= 0.08:
        return [best_ref.id]
    return []


def _resolve_explicit_targets(query: str, paper_refs: Sequence[PaperReference]) -> list[int]:
    name_targets = _resolve_name_targets(query, paper_refs)
    numeric_targets = _resolve_numeric_targets(query, paper_refs)
    return _dedupe_preserving_order([*name_targets, *numeric_targets])


def _recent_source_paper_ids(message: Message, valid_paper_ids: set[int]) -> list[int]:
    if message.role != "assistant":
        return []
    paper_ids: list[int] = []
    for source in message.sources or []:
        paper_id = source.get("paper_id")
        if isinstance(paper_id, int) and paper_id in valid_paper_ids:
            paper_ids.append(paper_id)
    return _dedupe_preserving_order(paper_ids)


def _recent_targets(
    recent_messages: Sequence[Message],
    paper_refs: Sequence[PaperReference],
) -> RecentTargets:
    valid_paper_ids = {paper_ref.id for paper_ref in paper_refs}

    ordered_messages = sorted(
        recent_messages,
        key=_message_sort_key,
    )
    single_ids: list[int] = []
    multi_ids: list[int] = []

    for message in reversed(ordered_messages[-MAX_RECENT_MESSAGES:]):
        explicit_targets = _resolve_explicit_targets(message.content, paper_refs)
        if explicit_targets:
            if len(explicit_targets) == 1 and not single_ids:
                single_ids = explicit_targets
            elif len(explicit_targets) > 1 and not multi_ids:
                multi_ids = explicit_targets
            if single_ids and multi_ids:
                break
            continue

        source_targets = _recent_source_paper_ids(message, valid_paper_ids)
        if source_targets:
            if len(source_targets) == 1 and not single_ids:
                single_ids = source_targets
            elif len(source_targets) > 1 and not multi_ids:
                multi_ids = source_targets
            if single_ids and multi_ids:
                break

    return RecentTargets(
        single_ids=single_ids,
        multi_ids=multi_ids,
    )


def _is_paper_target_clarification(content: str) -> bool:
    normalized = _normalize_text(content)
    return normalized.startswith(
        (
            "which paper",
            "which papers",
            "what should i compare it with",
            "select one or more papers first",
        )
    )


def _latest_pending_clarification(
    recent_messages: Sequence[Message],
) -> PendingClarification | None:
    ordered_messages = sorted(
        recent_messages,
        key=_message_sort_key,
    )
    if not ordered_messages or ordered_messages[-1].role != "assistant":
        return None

    last_assistant = ordered_messages[-1]
    if not _is_paper_target_clarification(last_assistant.content):
        return None

    for message in reversed(ordered_messages[:-1]):
        if message.role != "user":
            continue
        query = message.content.strip()
        request_type = _classify_request(query)
        return PendingClarification(
            query=query,
            request_type=request_type,
            reference_kind=_reference_kind(query, request_type),
        )

    return None


def _extract_assistant_offer_query(content: str) -> str | None:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(content.split()).strip())
    for sentence in reversed(sentences):
        normalized = _normalize_text(sentence)
        if not normalized:
            continue
        match = re.search(
            r"(?:if you want\s+)?i can(?: also)?\s+(?P<action>.+?)(?:\s+if you want)?$",
            normalized,
        )
        if not match:
            match = re.search(
                r"(?:if you want\s+)?i could(?: also)?\s+(?P<action>.+?)(?:\s+if you want)?$",
                normalized,
            )
        if not match:
            continue
        action = match.group("action").strip()
        if action.startswith(OFFER_ACTION_VERBS):
            return action
    return None


def _latest_pending_offer(
    recent_messages: Sequence[Message],
) -> PendingAssistantOffer | None:
    ordered_messages = sorted(
        recent_messages,
        key=_message_sort_key,
    )
    if not ordered_messages or ordered_messages[-1].role != "assistant":
        return None

    action_query = _extract_assistant_offer_query(ordered_messages[-1].content)
    if not action_query:
        return None

    for message in reversed(ordered_messages[:-1]):
        if message.role != "user":
            continue
        return PendingAssistantOffer(
            action_query=action_query,
            context_query=message.content.strip(),
        )

    return None


def _latest_topic_fragment(recent_messages: Sequence[Message]) -> str:
    ordered_messages = sorted(
        recent_messages,
        key=_message_sort_key,
    )
    for message in reversed(ordered_messages):
        if message.role != "user":
            continue
        if _is_affirmative_continuation(message.content):
            continue
        topic = _query_topic_fragment(message.content)
        if topic:
            return topic
    return ""


def _augment_query_with_recent_topic(
    query: str,
    *,
    preferred_context_query: str | None,
    recent_messages: Sequence[Message],
) -> str:
    if _query_topic_fragment(query):
        return query

    topic = _query_topic_fragment(preferred_context_query or "")
    if not topic:
        topic = _latest_topic_fragment(recent_messages)
    if not topic:
        return query

    normalized_query = _normalize_text(query)
    if topic in normalized_query:
        return query

    return f"{query} about {topic}"


def _is_target_only_reply(
    query: str,
    *,
    target_ids: Sequence[int],
    paper_ref_by_id: dict[int, PaperReference],
    selected_reference_kind: str | None,
    explicit_all: bool,
) -> bool:
    normalized = _normalize_text(query)
    if not normalized:
        return False

    working = f" {normalized} "
    for paper_id in target_ids:
        paper_ref = paper_ref_by_id.get(paper_id)
        if paper_ref is None:
            continue
        for alias in paper_ref.aliases:
            if len(alias) < 3:
                continue
            working = working.replace(f" {alias} ", " ")

    remaining_tokens = []
    for token in working.split():
        if token.isdigit() or re.fullmatch(r"\d+(?:st|nd|rd|th)", token):
            continue
        if token in CLARIFICATION_REPLY_FILLER_WORDS:
            continue
        if token in ORDINAL_WORDS:
            continue
        remaining_tokens.append(token)

    if remaining_tokens:
        return False

    return bool(target_ids or selected_reference_kind or explicit_all)


def _looks_like_follow_up(query: str) -> bool:
    normalized = f" {_normalize_text(query)} "
    if any(normalized.strip().startswith(prefix.strip()) for prefix in FOLLOW_UP_PREFIXES):
        return True
    if any(phrase in normalized for phrase in SINGULAR_PAPER_REFERENCE_PHRASES):
        return True
    if any(phrase in normalized for phrase in PLURAL_PAPER_REFERENCE_PHRASES):
        return True
    if any(phrase in normalized for phrase in SINGULAR_PRONOUN_REFERENCE_PHRASES):
        return True
    if any(phrase in normalized for phrase in PLURAL_PRONOUN_REFERENCE_PHRASES):
        return True
    if "results" in normalized or "limitation" in normalized or "objective" in normalized:
        return True
    return len(normalized.split()) <= 8 and normalized.strip().startswith(("what", "which", "how", "why"))


def _selected_reference_kind(query: str) -> str | None:
    normalized = f" {_normalize_text(query)} "
    if " selected papers " in normalized:
        return "plural"
    if " selected paper " in normalized:
        return "singular"
    return None


def _reference_kind(query: str, request_type: str) -> str | None:
    normalized = f" {_normalize_text(query)} "
    if _looks_like_identification_query(query, request_type):
        return None
    if any(phrase in normalized for phrase in PLURAL_PAPER_REFERENCE_PHRASES):
        return "paper_plural"
    if any(phrase in normalized for phrase in SINGULAR_PAPER_REFERENCE_PHRASES):
        return "paper_singular"
    if any(phrase in normalized for phrase in PLURAL_PRONOUN_REFERENCE_PHRASES):
        return "pronoun_plural"
    if any(phrase in normalized for phrase in SINGULAR_PRONOUN_REFERENCE_PHRASES):
        return "pronoun_singular"
    if " papers " in normalized and not _is_explicit_all(query):
        return "paper_plural"
    if (
        re.search(r"\bpaper\b", normalized)
        and not re.search(r"\bpaper(?:\s+number)?\s+\d+\b", normalized)
        and not _is_explicit_all(query)
    ):
        return "paper_singular"
    if request_type == "compare":
        return "paper_plural"
    return None


def _compose_retrieval_query(query: str, target_labels: Sequence[str]) -> str:
    if not target_labels:
        return query.strip()
    return f"{query.strip()}\nPaper scope: {', '.join(target_labels)}"


def _labels_for_ids(
    paper_ids: Sequence[int],
    paper_ref_by_id: dict[int, PaperReference],
) -> list[str]:
    return [paper_ref_by_id[paper_id].label for paper_id in paper_ids if paper_id in paper_ref_by_id]


def _paper_target_clarification_text(
    request_type: str,
    reference_kind: str | None,
    *,
    known_compare_target_count: int = 0,
) -> str:
    if request_type == "compare":
        if known_compare_target_count == 1:
            return COMPARE_WITH_CLARIFICATION_TEXT
        return COMPARE_PAPERS_CLARIFICATION_TEXT
    if request_type == "summary":
        if reference_kind in {"paper_plural", "pronoun_plural"}:
            return SUMMARY_PAPERS_CLARIFICATION_TEXT
        return SUMMARY_PAPER_CLARIFICATION_TEXT
    if reference_kind in {"paper_plural", "pronoun_plural"}:
        return PAPERS_CLARIFICATION_TEXT
    return PAPER_CLARIFICATION_TEXT


def _has_recent_referent(recent_targets: RecentTargets) -> bool:
    return bool(recent_targets.single_ids or recent_targets.multi_ids)


def _has_project_scope_cue(query: str) -> bool:
    normalized = _normalize_text(query)
    if any(f" {word} " in f" {normalized} " for word in PROJECT_SCOPE_CUE_WORDS):
        return True
    if _is_explicit_all(query):
        return True
    return bool(_tokenize(normalized) & PAPER_ANALYSIS_WORDS)


def _looks_like_out_of_scope_query(
    *,
    query: str,
    explicit_targets: Sequence[int],
    selected_ids: Sequence[int],
    recent_targets: RecentTargets,
) -> bool:
    if explicit_targets or selected_ids or _has_recent_referent(recent_targets):
        return False
    if _has_project_scope_cue(query):
        return False
    return True


def _resolve_compare_scope(
    *,
    explicit_targets: Sequence[int],
    selected_ids: Sequence[int],
    recent_targets: RecentTargets,
) -> tuple[list[int], str]:
    if len(explicit_targets) >= 2:
        return list(explicit_targets), "explicit"

    if explicit_targets:
        for context_ids, scope_source in (
            (selected_ids, "selected_scope"),
            (recent_targets.multi_ids, "recent_memory"),
            (recent_targets.single_ids, "recent_memory"),
        ):
            merged = _dedupe_preserving_order([*(context_ids or []), *explicit_targets])
            if len(merged) >= 2:
                return merged, scope_source
        return list(explicit_targets), "explicit"

    if len(selected_ids) > 1:
        return list(selected_ids), "selected_scope"

    if recent_targets.multi_ids:
        if len(selected_ids) == 1:
            merged = _dedupe_preserving_order([*selected_ids, *recent_targets.multi_ids])
            if len(merged) >= 2:
                return merged, "selected_scope"
        return list(recent_targets.multi_ids), "recent_memory"

    if len(selected_ids) == 1:
        merged = _dedupe_preserving_order([*selected_ids, *recent_targets.single_ids])
        if len(merged) >= 2:
            return merged, "selected_scope"
        return list(selected_ids), "selected_scope"

    if recent_targets.single_ids:
        return list(recent_targets.single_ids), "recent_memory"

    return [], "clarification"


def build_answer_plan(
    *,
    query: str,
    scope_paper_ids: Sequence[int] | None,
) -> AnswerPlan:
    request_type = _classify_request(query)
    scope_size = len(scope_paper_ids or [])
    quote_intent = _has_quote_intent(query)

    if quote_intent:
        if scope_size > 1:
            return AnswerPlan(
                request_type=request_type,
                response_mode="multi-paper quote extraction",
                organize_by="paper",
            )
        if scope_size == 1:
            return AnswerPlan(
                request_type=request_type,
                response_mode="single-paper quote extraction",
                organize_by="paper",
            )
        return AnswerPlan(
            request_type=request_type,
            response_mode="project-wide quote extraction",
            organize_by="paper",
        )

    if scope_size > 1:
        if request_type == "compare":
            return AnswerPlan(
                request_type=request_type,
                response_mode="multi-paper comparison",
                organize_by="comparison axis",
                prefer_table=True,
            )
        if request_type == "evidence":
            return AnswerPlan(
                request_type=request_type,
                response_mode="multi-paper evidence synthesis",
                organize_by="paper",
            )
        return AnswerPlan(
            request_type=request_type,
            response_mode="multi-paper summary",
            organize_by="paper",
        )

    if scope_size == 1:
        if request_type == "summary":
            response_mode = "single-paper summary"
        elif request_type == "evidence":
            response_mode = "single-paper evidence"
        else:
            response_mode = "single-paper answer"
        return AnswerPlan(
            request_type=request_type,
            response_mode=response_mode,
            organize_by="direct answer",
        )

    return AnswerPlan(
        request_type=request_type,
        response_mode="project-wide answer",
        organize_by="direct answer",
    )


def _effective_max_output_tokens(
    requested_tokens: int,
    answer_plan: AnswerPlan,
    scope_paper_ids: Sequence[int] | None,
) -> int:
    scope_size = len(scope_paper_ids or [])
    if scope_size <= 1:
        return requested_tokens

    floor = 700 if answer_plan.request_type == "evidence" else 850
    ceiling = 1100 if answer_plan.request_type == "compare" else 1000
    return max(requested_tokens, min(ceiling, floor + max(0, scope_size - 2) * 80))


def _resolve_scope(
    *,
    query: str,
    project_papers: Sequence[Paper],
    selected_paper_ids: Sequence[int],
    paper_order_ids: Sequence[int],
    recent_messages: Sequence[Message],
) -> ScopeResolution:
    request_type = _classify_request(query)
    paper_refs = _build_paper_refs(project_papers, paper_order_ids)
    paper_ref_by_id = {paper_ref.id: paper_ref for paper_ref in paper_refs}
    all_paper_ids = [paper_ref.id for paper_ref in paper_refs]
    selected_ids = [paper_id for paper_id in selected_paper_ids if paper_id in paper_ref_by_id]
    recent_history = _build_recent_history(recent_messages)
    recent_targets = _recent_targets(recent_messages, paper_refs)
    pending_clarification = _latest_pending_clarification(recent_messages)
    pending_offer = _latest_pending_offer(recent_messages)
    selected_reference_kind = _selected_reference_kind(query)
    explicit_all = _is_explicit_all(query)
    explicit_targets = _resolve_explicit_targets(query, paper_refs)
    use_pending_clarification = (
        pending_clarification is not None
        and request_type == "question"
        and _is_target_only_reply(
            query,
            target_ids=explicit_targets,
            paper_ref_by_id=paper_ref_by_id,
            selected_reference_kind=selected_reference_kind,
            explicit_all=explicit_all,
        )
    )
    use_pending_offer = (
        not use_pending_clarification
        and pending_offer is not None
        and request_type == "question"
        and _is_affirmative_continuation(query)
    )
    resolved_query = query.strip()
    if use_pending_clarification and pending_clarification is not None:
        resolved_query = pending_clarification.query.strip()
        request_type = pending_clarification.request_type
        reference_kind = pending_clarification.reference_kind or _reference_kind(
            pending_clarification.query,
            pending_clarification.request_type,
        )
    elif use_pending_offer and pending_offer is not None:
        resolved_query = _augment_query_with_recent_topic(
            pending_offer.action_query,
            preferred_context_query=pending_offer.context_query,
            recent_messages=recent_messages,
        )
        request_type = _classify_request(resolved_query)
        reference_kind = _reference_kind(resolved_query, request_type)
    else:
        reference_kind = _reference_kind(query, request_type)
        if _has_quote_intent(resolved_query):
            resolved_query = _augment_query_with_recent_topic(
                resolved_query,
                preferred_context_query=None,
                recent_messages=recent_messages,
            )
            request_type = _classify_request(resolved_query)
            reference_kind = _reference_kind(resolved_query, request_type)

    def scoped_resolution(
        paper_ids: Sequence[int],
        *,
        scope_source: str,
    ) -> ScopeResolution:
        target_ids = list(paper_ids)
        target_labels = _labels_for_ids(target_ids, paper_ref_by_id)
        return ScopeResolution(
            paper_ids=target_ids,
            target_labels=target_labels,
            scope_source=scope_source,
            recent_history=recent_history,
            resolved_query=resolved_query,
            retrieval_query=_compose_retrieval_query(resolved_query, target_labels),
            request_type=request_type,
            reference_kind=reference_kind,
        )

    def clarification_resolution(text: str) -> ScopeResolution:
        return ScopeResolution(
            paper_ids=None,
            target_labels=[],
            scope_source="clarification",
            recent_history=recent_history,
            resolved_query=resolved_query,
            retrieval_query=resolved_query,
            request_type=request_type,
            reference_kind=reference_kind,
            assistant_action="clarify",
            clarification_text=text,
        )

    def project_scope_resolution() -> ScopeResolution:
        return ScopeResolution(
            paper_ids=None,
            target_labels=[],
            scope_source="project_scope",
            recent_history=recent_history,
            resolved_query=resolved_query,
            retrieval_query=resolved_query,
            request_type=request_type,
            reference_kind=reference_kind,
        )

    if _is_project_help_request(query, explicit_targets):
        return ScopeResolution(
            paper_ids=None,
            target_labels=[],
            scope_source="help",
            recent_history=recent_history,
            resolved_query=resolved_query,
            retrieval_query=resolved_query,
            request_type=request_type,
            reference_kind=reference_kind,
            assistant_response=_help_response_for(query),
            assistant_action="answer",
        )

    if _looks_like_cross_paper_discovery_query(resolved_query, request_type):
        if not _discovery_target_fragment(resolved_query):
            return clarification_resolution(DISCOVERY_CLARIFICATION_TEXT)
        if explicit_all:
            return scoped_resolution(all_paper_ids or [], scope_source="all_scope")
        if selected_ids:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        return project_scope_resolution()

    if _looks_like_out_of_scope_query(
        query=resolved_query,
        explicit_targets=explicit_targets,
        selected_ids=selected_ids,
        recent_targets=recent_targets,
    ):
        return ScopeResolution(
            paper_ids=None,
            target_labels=[],
            scope_source="out_of_scope",
            recent_history=recent_history,
            resolved_query=resolved_query,
            retrieval_query=resolved_query,
            request_type=request_type,
            reference_kind=reference_kind,
            assistant_response=OUT_OF_SCOPE_REFUSAL_TEXT,
            assistant_action="refuse",
        )

    if explicit_targets:
        if request_type == "compare":
            compare_targets, scope_source = _resolve_compare_scope(
                explicit_targets=explicit_targets,
                selected_ids=selected_ids,
                recent_targets=recent_targets,
            )
            if len(compare_targets) >= 2:
                return scoped_resolution(compare_targets, scope_source=scope_source)
            return clarification_resolution(
                _paper_target_clarification_text(
                    request_type,
                    reference_kind,
                    known_compare_target_count=len(compare_targets),
                )
            )

        return scoped_resolution(explicit_targets, scope_source="explicit")

    if selected_reference_kind == "plural":
        if not selected_ids:
            return clarification_resolution(SELECTED_PAPER_CLARIFICATION_TEXT)
        return scoped_resolution(selected_ids, scope_source="selected_scope")

    if selected_reference_kind == "singular":
        if not selected_ids:
            return clarification_resolution(SELECTED_PAPER_CLARIFICATION_TEXT)
        target_ids = selected_ids[:1] if len(selected_ids) == 1 else selected_ids
        return scoped_resolution(target_ids, scope_source="selected_scope")

    if explicit_all:
        return scoped_resolution(all_paper_ids or [], scope_source="all_scope")

    if request_type == "compare":
        compare_targets, scope_source = _resolve_compare_scope(
            explicit_targets=[],
            selected_ids=selected_ids,
            recent_targets=recent_targets,
        )
        if len(compare_targets) >= 2:
            return scoped_resolution(compare_targets, scope_source=scope_source)
        return clarification_resolution(
            _paper_target_clarification_text(
                request_type,
                reference_kind,
                known_compare_target_count=len(compare_targets),
            )
        )

    if _looks_like_identification_query(resolved_query, request_type):
        if selected_ids:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        return project_scope_resolution()

    if reference_kind == "paper_singular":
        if selected_ids:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        if recent_targets.single_ids:
            return scoped_resolution(recent_targets.single_ids, scope_source="recent_memory")
        return clarification_resolution(_paper_target_clarification_text(request_type, reference_kind))

    if reference_kind == "paper_plural":
        if len(selected_ids) > 1:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        if recent_targets.multi_ids:
            return scoped_resolution(recent_targets.multi_ids, scope_source="recent_memory")
        return clarification_resolution(_paper_target_clarification_text(request_type, reference_kind))

    if reference_kind == "pronoun_singular":
        if len(selected_ids) == 1:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        if recent_targets.single_ids:
            return scoped_resolution(recent_targets.single_ids, scope_source="recent_memory")
        if len(selected_ids) > 1:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        return clarification_resolution(_paper_target_clarification_text(request_type, reference_kind))

    if reference_kind == "pronoun_plural":
        if len(selected_ids) > 1:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        if recent_targets.multi_ids:
            return scoped_resolution(recent_targets.multi_ids, scope_source="recent_memory")
        if recent_targets.single_ids:
            return scoped_resolution(recent_targets.single_ids, scope_source="recent_memory")
        if len(selected_ids) == 1:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        return clarification_resolution(_paper_target_clarification_text(request_type, reference_kind))

    if _looks_like_follow_up(query):
        if selected_ids:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        if recent_targets.single_ids:
            return scoped_resolution(recent_targets.single_ids, scope_source="recent_memory")
        if recent_targets.multi_ids:
            return scoped_resolution(recent_targets.multi_ids, scope_source="recent_memory")

    if request_type == "summary":
        if selected_ids:
            return scoped_resolution(selected_ids, scope_source="selected_scope")
        if recent_targets.single_ids:
            return scoped_resolution(recent_targets.single_ids, scope_source="recent_memory")
        if recent_targets.multi_ids:
            return scoped_resolution(recent_targets.multi_ids, scope_source="recent_memory")
        return clarification_resolution(_paper_target_clarification_text(request_type, reference_kind))

    if selected_ids:
        return scoped_resolution(selected_ids, scope_source="selected_scope")

    return project_scope_resolution()


def _retrieve_hits(
    *,
    project_slug: str,
    retrieval_query: str,
    top_k: int,
    scope_paper_ids: list[int] | None,
    request_type: str,
) -> list[dict]:
    if not scope_paper_ids:
        return hybrid_retrieve(
            project_slug=project_slug,
            query=retrieval_query,
            top_k=top_k,
        )

    if len(scope_paper_ids) == 1:
        return hybrid_retrieve(
            project_slug=project_slug,
            query=retrieval_query,
            top_k=max(top_k, 6 if request_type == "question" else 8),
            paper_ids=scope_paper_ids,
        )

    if request_type == "compare":
        per_paper_limit = 3
        retrieval_budget = max(top_k, min(18, max(8, len(scope_paper_ids) * 3)))
    elif request_type == "summary":
        per_paper_limit = 3
        retrieval_budget = max(top_k, min(20, max(8, len(scope_paper_ids) * 3)))
    elif request_type == "evidence":
        per_paper_limit = 2
        retrieval_budget = max(top_k, min(18, max(8, len(scope_paper_ids) * 3)))
    else:
        per_paper_limit = 2 if len(scope_paper_ids) <= 4 else 1
        retrieval_budget = max(top_k, min(14, max(6, len(scope_paper_ids) * 2)))
    combined_hits: list[dict] = []

    for paper_id in scope_paper_ids:
        combined_hits.extend(
            hybrid_retrieve(
                project_slug=project_slug,
                query=retrieval_query,
                top_k=per_paper_limit,
                paper_ids=[paper_id],
            )
        )

    combined_hits.extend(
        hybrid_retrieve(
            project_slug=project_slug,
            query=retrieval_query,
            top_k=retrieval_budget,
            paper_ids=scope_paper_ids,
        )
    )

    return _merge_hits(combined_hits, top_k=retrieval_budget)


def _has_sufficient_evidence(
    query: str,
    hits: list[dict],
    scope_paper_ids: list[int] | None,
    request_type: str,
) -> bool:
    if not hits:
        return False

    covered_papers = {hit["paper_id"] for hit in hits[: max(6, len(scope_paper_ids or []) * 3)]}

    if scope_paper_ids:
        in_scope_coverage = covered_papers & set(scope_paper_ids)
        if request_type == "summary":
            return bool(in_scope_coverage)
        if request_type == "compare":
            return bool(in_scope_coverage)
        if request_type == "evidence" and not in_scope_coverage:
            return False
        if len(scope_paper_ids) == 1:
            return scope_paper_ids[0] in in_scope_coverage
        if request_type != "evidence" and in_scope_coverage:
            return True

    if request_type == "summary":
        return True

    if request_type == "compare":
        return len(covered_papers) >= 2

    query_tokens = _tokenize(query)
    if not query_tokens:
        return False

    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "what", "how", "who",
        "does", "did", "do", "in", "on", "of", "for", "to", "and", "with"
    }
    query_tokens = {token for token in query_tokens if token not in stopwords and len(token) > 2}

    if not query_tokens:
        return bool(scope_paper_ids and hits)

    best_overlap = 0
    best_ratio = 0.0

    for hit in hits[:5]:
        text_tokens = _tokenize(hit["text"])
        overlap = len(query_tokens & text_tokens)
        ratio = overlap / len(query_tokens)

        best_overlap = max(best_overlap, overlap)
        best_ratio = max(best_ratio, ratio)

    if best_overlap >= 2:
        return True

    if best_ratio >= 0.5:
        return True

    if request_type in {"summary", "compare"} and len(covered_papers) >= 2:
        return True

    return False


def _insufficient_text(scope_source: str, scope_paper_ids: Sequence[int] | None = None) -> str:
    if scope_source == "selected_scope" and scope_paper_ids:
        return SELECTED_SCOPE_INSUFFICIENT_TEXT
    return INSUFFICIENT_EVIDENCE_TEXT


def _is_full_insufficient_answer(answer: str) -> bool:
    normalized = _normalize_text(answer)
    if not normalized:
        return False

    for prefix in FULL_INSUFFICIENT_ANSWER_PREFIXES:
        if normalized == prefix:
            return True
        if normalized.startswith(prefix) and len(normalized.split()) <= len(prefix.split()) + 4:
            return True

    return False


def _strip_trailing_low_value_unsupported_addendum(
    answer: str,
    *,
    request_type: str,
) -> str:
    if request_type == "evidence":
        return answer.strip()

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", answer.strip()) if part.strip()]
    if len(paragraphs) < 2:
        return answer.strip()

    prior_content = "\n\n".join(paragraphs[:-1]).strip()
    if not prior_content or not SOURCE_TAG_RE.search(prior_content):
        return answer.strip()

    last_normalized = _normalize_text(paragraphs[-1])
    if not any(last_normalized.startswith(prefix) for prefix in LOW_VALUE_UNSUPPORTED_PREFIXES):
        return answer.strip()

    return "\n\n".join(paragraphs[:-1]).strip()


def ask_project(
    project_id: int,
    project_slug: str,
    query: str,
    top_k: int,
    temperature: float,
    max_output_tokens: int,
    project_papers: Sequence[Paper],
    recent_messages: Sequence[Message] = (),
    selected_paper_ids: Sequence[int] = (),
    paper_order_ids: Sequence[int] = (),
) -> dict:
    total_start = time.perf_counter()

    def finish(
        payload: dict,
        *,
        retrieval_latency_sec: float | None = None,
        generation_latency_sec: float | None = None,
        generation: LLMGenerationResult | None = None,
    ) -> dict:
        payload["timing"] = {
            "retrieval_latency_sec": retrieval_latency_sec,
            "generation_latency_sec": generation_latency_sec,
            "total_latency_sec": round(time.perf_counter() - total_start, 6),
        }
        payload["usage"] = (
            {
                "llm_provider": generation.provider,
                "llm_model": generation.model,
                "input_tokens": generation.input_tokens,
                "output_tokens": generation.output_tokens,
                "total_tokens": generation.total_tokens,
            }
            if generation is not None
            else None
        )
        return payload

    scope = _resolve_scope(
        query=query,
        project_papers=project_papers,
        selected_paper_ids=selected_paper_ids,
        paper_order_ids=paper_order_ids,
        recent_messages=recent_messages,
    )

    if scope.assistant_response:
        return finish({
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": scope.assistant_response,
            "action": scope.assistant_action or "answer",
            "insufficient_evidence": False,
            "retrieval_hits_count": 0,
            "used_sources": [],
        })

    if scope.clarification_text:
        return finish({
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": scope.clarification_text,
            "action": "clarify",
            "insufficient_evidence": False,
            "retrieval_hits_count": 0,
            "used_sources": [],
        })

    answer_plan = build_answer_plan(
        query=scope.resolved_query,
        scope_paper_ids=scope.paper_ids,
    )

    retrieval_start = time.perf_counter()
    hits = _retrieve_hits(
        project_slug=project_slug,
        retrieval_query=scope.retrieval_query,
        top_k=top_k,
        scope_paper_ids=scope.paper_ids,
        request_type=answer_plan.request_type,
    )
    retrieval_latency_sec = round(time.perf_counter() - retrieval_start, 6)

    if not hits:
        return finish({
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": _insufficient_text(scope.scope_source, scope.paper_ids),
            "action": "refuse",
            "insufficient_evidence": True,
            "retrieval_hits_count": 0,
            "used_sources": [],
        }, retrieval_latency_sec=retrieval_latency_sec)

    if not _has_sufficient_evidence(scope.resolved_query, hits, scope.paper_ids, answer_plan.request_type):
        return finish({
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": _insufficient_text(scope.scope_source, scope.paper_ids),
            "action": "refuse",
            "insufficient_evidence": True,
            "retrieval_hits_count": len(hits),
            "used_sources": [],
        }, retrieval_latency_sec=retrieval_latency_sec)

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        query=scope.resolved_query,
        hits=hits,
        recent_messages=scope.recent_history,
        target_papers=scope.target_labels,
        answer_plan={
            "request_type": answer_plan.request_type,
            "response_mode": answer_plan.response_mode,
            "organize_by": answer_plan.organize_by,
            "prefer_table": "yes" if answer_plan.prefer_table else "no",
        },
    )

    generation_start = time.perf_counter()
    generation = generate_answer(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_output_tokens=_effective_max_output_tokens(
            max_output_tokens,
            answer_plan,
            scope.paper_ids,
        ),
    )
    generation_latency_sec = round(time.perf_counter() - generation_start, 6)
    answer = generation.text

    answer = _normalize_citation_groups(answer)
    answer = _strip_trailing_low_value_unsupported_addendum(
        answer,
        request_type=answer_plan.request_type,
    )
    if _is_full_insufficient_answer(answer):
        return finish({
            "project_id": project_id,
            "project_slug": project_slug,
            "query": query,
            "answer": _insufficient_text(scope.scope_source, scope.paper_ids),
            "action": "refuse",
            "insufficient_evidence": True,
            "retrieval_hits_count": len(hits),
            "used_sources": [],
        }, retrieval_latency_sec=retrieval_latency_sec, generation_latency_sec=generation_latency_sec, generation=generation)

    cited_source_numbers = _extract_cited_source_numbers(answer, len(hits))

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

    return finish({
        "project_id": project_id,
        "project_slug": project_slug,
        "query": query,
        "answer": answer,
        "action": "answer",
        "insufficient_evidence": False,
        "retrieval_hits_count": len(hits),
        "used_sources": used_sources,
    }, retrieval_latency_sec=retrieval_latency_sec, generation_latency_sec=generation_latency_sec, generation=generation)

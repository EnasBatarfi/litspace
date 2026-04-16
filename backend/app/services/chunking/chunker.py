# This module provides functionality to chunk a processed document into smaller pieces suitable for indexing and retrieval.

from __future__ import annotations

import math
import re
from typing import Any


MINIMAL_EXACT_HEADINGS = {
    "abstract",
    "references",
    "bibliography",
}

CAPTION_RE = re.compile(r"^(Figure|Fig\.|Table|Algorithm)\s+\d+[:.]?", re.IGNORECASE)
SECTION_NUMBER_ONLY_RE = re.compile(r"^\d+(?:\.\d+)*$")
LETTERED_APPENDIX_LABEL_RE = re.compile(r"^[A-Z](?:\.\d+)*$")
NUMBERED_HEADING_RE = re.compile(
    r"^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-Z][A-Za-z0-9()/:,\-–'’ ]{2,140})$"
)
APPENDIX_HEADING_RE = re.compile(
    r"^(Appendix(?:\s+[A-Z0-9]+)?)(?::|\s+|-)?(?P<title>.*)$",
    re.IGNORECASE,
)
LETTERED_APPENDIX_HEADING_RE = re.compile(
    r"^(?P<label>[A-Z](?:\.\d+)*)\s+(?P<title>[A-Z][A-Za-z0-9()/:,\-–'’ ]{2,140})$"
)
ARXIV_FOOTER_RE = re.compile(r"^arxiv:\S+", re.IGNORECASE)
URL_RE = re.compile(r"(https?://|www\.)", re.IGNORECASE)
CITATION_START_RE = re.compile(r"^\[\d+\]")
CODEISH_RE = re.compile(r"(::=|==|(?<![<>=!])=(?![=>])|//|[{]|[}]|=>)")
BULLETISH_RE = re.compile(r"^[•\-*]\s*")
WORD_RE = re.compile(r"[A-Za-z0-9]+")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return max(1, math.ceil(words * 1.3))


def clean_line(line: str) -> str:
    line = line.replace("\u00ad", "")
    line = line.replace("\xa0", " ")
    return normalize_whitespace(line)


def is_noise_line(line: str) -> bool:
    if not line:
        return True

    if re.fullmatch(r"\d{1,3}", line):
        return True

    if ARXIV_FOOTER_RE.match(line):
        return True

    lower = line.lower()
    if lower.startswith("proceedings of") or lower.startswith("preprint"):
        return True

    return False


def join_wrapped_lines(lines: list[str]) -> str:
    if not lines:
        return ""

    text = lines[0]
    for line in lines[1:]:
        if text.endswith("-") and line and line[0].islower():
            text = text[:-1] + line
        else:
            text = f"{text} {line}"

    return normalize_whitespace(text)


def significant_words(words: list[str]) -> list[str]:
    out: list[str] = []
    for word in words:
        stripped = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", word)
        if stripped:
            out.append(stripped)
    return out


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def titlecase_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    cap = sum(1 for w in words if w[0].isupper())
    return cap / len(words)


def is_symbol_heavy(text: str) -> bool:
    symbols = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
    return symbols > max(6, len(text) * 0.12)


def ends_like_wrapped_prose(text: str) -> bool:
    words = significant_words(text.split())
    if not words:
        return True
    if text.endswith("-"):
        return True
    last = words[-1]
    return bool(last and last[0].islower())


def is_short_data_label(text: str) -> bool:
    words = significant_words(text.split())
    if not words:
        return True

    if len(words) == 1:
        word = words[0]
        if word.lower() in MINIMAL_EXACT_HEADINGS:
            return False
        return len(word) < 8

    # Table headers and diagram labels are often tiny title-cased fragments.
    return len(words) <= 3 and sum(len(word) for word in words) <= 14


def is_likely_author_or_affiliation_block(text: str) -> bool:
    lower = text.lower()
    if "@" in text:
        return True

    affiliation_terms = (
        "university",
        "institute",
        "college",
        "school",
        "department",
        "laboratory",
        "lab",
    )
    if any(term in lower for term in affiliation_terms):
        return True

    words = significant_words(text.split())
    return "," in text and len(words) >= 4


def looks_like_title_fragment(text: str) -> bool:
    if not text:
        return False
    if CAPTION_RE.match(text) or URL_RE.search(text) or CODEISH_RE.search(text):
        return False
    if text.endswith(".") or text.endswith(";"):
        return False
    if is_symbol_heavy(text):
        return False

    words = significant_words(text.split())
    if len(words) < 3 or len(words) > 20:
        return False

    return text[:1].isupper() and titlecase_ratio(words) >= 0.35


def has_real_prose_nearby(text: str | None) -> bool:
    if not text:
        return False
    prefix = text[:240]
    if CAPTION_RE.match(prefix) or CODEISH_RE.search(prefix) or BULLETISH_RE.match(prefix):
        return False
    if is_symbol_heavy(prefix):
        return False
    return word_count(text) >= 8


def has_appendix_content_nearby(text: str | None) -> bool:
    if not text:
        return False

    normalized = normalize_whitespace(text)
    if LETTERED_APPENDIX_LABEL_RE.fullmatch(normalized):
        return True

    prefix = normalized[:240]
    if CODEISH_RE.search(prefix) or is_symbol_heavy(prefix):
        return False

    return word_count(normalized) >= 5


def looks_like_numbered_heading_title(title: str, next_block_text: str | None) -> bool:
    title = normalize_whitespace(title)
    if not title:
        return False
    if CAPTION_RE.match(title) or CODEISH_RE.search(title) or URL_RE.search(title):
        return False
    if re.search(r"[(){}]", title):
        return False
    if is_symbol_heavy(title) or ends_like_wrapped_prose(title):
        return False

    words = significant_words(title.split())
    if not words or len(words) > 12:
        return False

    if titlecase_ratio(words) < 0.5:
        return False

    return has_real_prose_nearby(next_block_text)


def looks_like_lettered_appendix_heading(
    label: str,
    title: str,
    next_block_text: str | None,
) -> bool:
    if not LETTERED_APPENDIX_LABEL_RE.fullmatch(label):
        return False

    title = normalize_whitespace(title)
    if not title:
        return False

    if CAPTION_RE.match(title) or CODEISH_RE.search(title) or URL_RE.search(title):
        return False

    if title.endswith(".") or title.endswith(",") or title.endswith(";"):
        return False

    if is_symbol_heavy(title):
        return False

    words = significant_words(title.split())
    if not words or len(words) > 12:
        return False

    if not words[0][0].isupper():
        return False

    # Lettered appendices often use sentence case, e.g. "A Sample policies".
    if titlecase_ratio(words) < 0.35:
        return False

    return has_appendix_content_nearby(next_block_text)


def looks_like_heading_block(block_text: str, next_block_text: str | None) -> bool:
    lower = block_text.lower()

    if lower in MINIMAL_EXACT_HEADINGS:
        return True

    numbered = NUMBERED_HEADING_RE.match(block_text)
    if numbered:
        title = normalize_whitespace(numbered.group("title"))
        return looks_like_numbered_heading_title(title, next_block_text)

    if APPENDIX_HEADING_RE.match(block_text):
        return True

    lettered_appendix = LETTERED_APPENDIX_HEADING_RE.match(block_text)
    if lettered_appendix:
        return looks_like_lettered_appendix_heading(
            label=lettered_appendix.group("label"),
            title=lettered_appendix.group("title"),
            next_block_text=next_block_text,
        )

    if CAPTION_RE.match(block_text):
        return False

    if CITATION_START_RE.match(block_text):
        return False

    if URL_RE.search(block_text):
        return False

    if CODEISH_RE.search(block_text):
        return False

    if BULLETISH_RE.match(block_text):
        return False

    if is_symbol_heavy(block_text):
        return False

    if len(block_text) > 120:
        return False

    if ends_like_wrapped_prose(block_text):
        return False

    if block_text.endswith(".") or block_text.endswith(",") or block_text.endswith(";"):
        return False

    words = significant_words(block_text.split())
    if not words:
        return False

    if len(words) > 12:
        return False

    if is_short_data_label(block_text):
        return False

    # Single-word headings are allowed only when the next block looks like real prose.
    if len(words) == 1:
        word = words[0]
        if len(word) < 5:
            return False
        if not word[0].isupper():
            return False
        if next_block_text and next_block_text[:1].islower():
            return False
        if not has_real_prose_nearby(next_block_text):
            return False
        return True

    # Multi-word headings should look title-like and lead into actual prose.
    if titlecase_ratio(words) < 0.7:
        return False

    if next_block_text and next_block_text[:1].islower():
        return False

    if next_block_text and not has_real_prose_nearby(next_block_text):
        return False

    return True


def extract_heading(block_text: str, next_block_text: str | None = None) -> dict[str, Any] | None:
    lower = block_text.lower()

    if lower in MINIMAL_EXACT_HEADINGS:
        return {
            "full_heading": block_text,
            "heading": block_text.title(),
            "path": [],
            "is_appendix": False,
        }

    numbered = NUMBERED_HEADING_RE.match(block_text)
    if numbered:
        num = numbered.group("num")
        title = normalize_whitespace(numbered.group("title"))
        if not looks_like_numbered_heading_title(title, next_block_text):
            return None
        return {
            "full_heading": f"{num} {title}",
            "heading": title,
            "path": num.split("."),
            "is_appendix": False,
        }

    appendix = APPENDIX_HEADING_RE.match(block_text)
    if appendix:
        appendix_label = normalize_whitespace(appendix.group(1))
        appendix_title = normalize_whitespace(appendix.group("title"))
        full_heading = appendix_label if not appendix_title else f"{appendix_label} {appendix_title}"
        return {
            "full_heading": full_heading,
            "heading": full_heading,
            "path": [appendix_label],
            "is_appendix": True,
        }

    lettered_appendix = LETTERED_APPENDIX_HEADING_RE.match(block_text)
    if lettered_appendix:
        label = lettered_appendix.group("label")
        title = normalize_whitespace(lettered_appendix.group("title"))
        if not looks_like_lettered_appendix_heading(label, title, next_block_text):
            return None
        return {
            "full_heading": f"{label} {title}",
            "heading": title,
            "path": label.split("."),
            "is_appendix": True,
        }

    if looks_like_heading_block(block_text, next_block_text):
        return {
            "full_heading": block_text,
            "heading": block_text,
            "path": [],
            "is_appendix": False,
        }

    return None


def get_clean_lines(raw_text: str) -> list[str]:
    return [clean_line(line) for line in raw_text.splitlines()]


def next_content_line(lines: list[str], start_index: int) -> str | None:
    for line in lines[start_index:]:
        if line and not is_noise_line(line):
            return line
    return None


def can_merge_split_heading(lines: list[str], index: int) -> bool:
    current = lines[index]
    if not (
        SECTION_NUMBER_ONLY_RE.fullmatch(current)
        or LETTERED_APPENDIX_LABEL_RE.fullmatch(current)
    ):
        return False

    heading_line = next_content_line(lines, index + 1)
    if not heading_line:
        return False

    try:
        heading_index = lines.index(heading_line, index + 1)
    except ValueError:
        heading_index = index + 1

    following = next_content_line(lines, heading_index + 1)
    return extract_heading(f"{current} {heading_line}", following) is not None


def split_page_into_structural_blocks(raw_text: str) -> list[dict[str, str]]:
    lines = get_clean_lines(raw_text)
    blocks: list[dict[str, str]] = []
    paragraph_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        text = join_wrapped_lines(paragraph_lines)
        if text:
            blocks.append({"kind": "paragraph", "text": text})
        paragraph_lines = []

    while index < len(lines):
        line = lines[index]
        if not line:
            flush_paragraph()
            index += 1
            continue

        if SECTION_NUMBER_ONLY_RE.fullmatch(line) or LETTERED_APPENDIX_LABEL_RE.fullmatch(line):
            if can_merge_split_heading(lines, index):
                heading_line = next_content_line(lines, index + 1)
                assert heading_line is not None
                heading_index = lines.index(heading_line, index + 1)
                following = next_content_line(lines, heading_index + 1)
                heading_text = f"{line} {heading_line}"
                heading = extract_heading(heading_text, following)
                if heading:
                    flush_paragraph()
                    block_kind = (
                        "appendix_candidate"
                        if heading["is_appendix"] and not heading_text.lower().startswith("appendix")
                        else "section_header"
                    )
                    blocks.append({"kind": block_kind, "text": heading_text})
                    index = heading_index + 1
                    continue

            # Standalone numbers are usually page numbers, table values, or algorithm line numbers.
            index += 1
            continue

        if is_noise_line(line):
            flush_paragraph()
            index += 1
            continue

        following = next_content_line(lines, index + 1)

        if CAPTION_RE.match(line):
            flush_paragraph()
            blocks.append({"kind": "caption", "text": line})
            index += 1
            continue

        heading = extract_heading(line, following)
        if heading is not None:
            flush_paragraph()
            block_kind = (
                "appendix_candidate"
                if heading["is_appendix"] and not heading["full_heading"].lower().startswith("appendix")
                else "section_header"
            )
            blocks.append({"kind": block_kind, "text": heading["full_heading"]})
            index += 1
            continue

        paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    return blocks


def merge_first_page_title_blocks(blocks: list[dict[str, str]]) -> list[dict[str, str]]:
    section_start: int | None = None
    for index, block in enumerate(blocks[:8]):
        text = block["text"].lower()
        if text == "abstract" or text == "1 introduction" or text == "introduction":
            section_start = index
            break

    if section_start is None or section_start == 0:
        return blocks

    prefix = blocks[:section_start]
    title_parts: list[str] = []
    remainder: list[dict[str, str]] = []

    for block in prefix:
        text = block["text"]
        if not title_parts and not looks_like_title_fragment(text):
            remainder.append(block)
            continue

        if title_parts and is_likely_author_or_affiliation_block(text):
            remainder.append(block)
            continue

        if len(title_parts) < 3 and looks_like_title_fragment(text):
            title_parts.append(text)
        else:
            remainder.append(block)

    if not title_parts:
        return blocks

    title_block = {
        "kind": "title",
        "text": normalize_whitespace(" ".join(title_parts)),
    }
    return [title_block, *remainder, *blocks[section_start:]]


def classify_block_type(block_text: str, current_section_heading: str | None) -> str:
    if CAPTION_RE.match(block_text):
        first = block_text.lower()
        if first.startswith("figure") or first.startswith("fig."):
            return "figure_caption"
        if first.startswith("table"):
            return "table_caption"
        if first.startswith("algorithm"):
            return "algorithm_caption"

    if (current_section_heading or "").lower() == "abstract":
        return "abstract"

    return "paragraph"


def split_long_text(text: str, max_tokens: int) -> list[str]:
    text = normalize_whitespace(text)
    if not text:
        return []

    if estimate_tokens(text) <= max_tokens:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    pieces: list[str] = []
    current: list[str] = []

    for sentence in sentences:
        sentence = normalize_whitespace(sentence)
        if not sentence:
            continue

        tentative = " ".join(current + [sentence]).strip()
        if current and estimate_tokens(tentative) > max_tokens:
            pieces.append(" ".join(current).strip())
            current = [sentence]
        else:
            current.append(sentence)

    if current:
        pieces.append(" ".join(current).strip())

    final_pieces: list[str] = []
    for piece in pieces:
        if estimate_tokens(piece) <= max_tokens:
            final_pieces.append(piece)
            continue

        words = piece.split()
        window: list[str] = []
        for word in words:
            tentative = " ".join(window + [word]).strip()
            if window and estimate_tokens(tentative) > max_tokens:
                final_pieces.append(" ".join(window).strip())
                window = [word]
            else:
                window.append(word)

        if window:
            final_pieces.append(" ".join(window).strip())

    return [p for p in final_pieces if p]


def extract_blocks(processed_doc: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    order = 0

    current_section_heading: str | None = None
    current_section_path: list[str] = []
    in_terminal_bibliography = False
    in_appendix = False
    saw_real_section = False

    for page in processed_doc["pages"]:
        page_number = page["page_number"]
        raw_text = page.get("text", "") or ""

        structural_blocks = split_page_into_structural_blocks(raw_text)
        if page_number == 1:
            structural_blocks = merge_first_page_title_blocks(structural_blocks)

        for idx, block in enumerate(structural_blocks):
            block_text = block["text"]
            next_block_text = (
                structural_blocks[idx + 1]["text"]
                if idx + 1 < len(structural_blocks)
                else None
            )
            next_few_texts = [
                future_block["text"].lower()
                for future_block in structural_blocks[idx + 1 : idx + 5]
            ]

            # Treat the first title-like block on page 1 before a real section as document title, not section heading.
            if (
                page_number == 1
                and not saw_real_section
                and order == 0
                and (
                    block["kind"] == "title"
                    or block["kind"] == "section_header"
                    or block["kind"] == "appendix_candidate"
                    or looks_like_heading_block(block_text, next_block_text)
                )
                and (
                    block["kind"] == "title"
                    or any(text in {"abstract", "introduction", "1 introduction"} for text in next_few_texts)
                )
            ):
                blocks.append(
                    {
                        "block_id": f"paper-{processed_doc['paper_id']}-block-{order:04d}",
                        "order": order,
                        "block_type": "title",
                        "text": block_text,
                        "page_start": page_number,
                        "page_end": page_number,
                        "section_heading": None,
                        "section_path": [],
                        "approx_tokens": estimate_tokens(block_text),
                    }
                )
                order += 1
                continue

            heading = (
                extract_heading(block_text, next_block_text)
                if block["kind"] == "section_header"
                or (
                    block["kind"] == "appendix_candidate"
                    and (in_terminal_bibliography or in_appendix)
                )
                else None
            )

            # Bibliography entries often look like title-cased headings. Keep them in the
            # References section, but do not mark or exclude them from indexing.
            if in_terminal_bibliography:
                if heading is not None and heading["is_appendix"]:
                    in_terminal_bibliography = False
                else:
                    block_type = classify_block_type(
                        block_text=block_text,
                        current_section_heading=current_section_heading,
                    )

                    blocks.append(
                        {
                            "block_id": f"paper-{processed_doc['paper_id']}-block-{order:04d}",
                            "order": order,
                            "block_type": block_type,
                            "text": block_text,
                            "page_start": page_number,
                            "page_end": page_number,
                            "section_heading": current_section_heading,
                            "section_path": current_section_path[:],
                            "approx_tokens": estimate_tokens(block_text),
                        }
                    )
                    order += 1
                    continue

            if heading is not None:
                current_section_heading = heading["heading"]
                current_section_path = heading["path"][:]
                in_appendix = bool(heading["is_appendix"])
                in_terminal_bibliography = current_section_heading.lower() in {
                    "references",
                    "bibliography",
                }
                saw_real_section = True

                blocks.append(
                    {
                        "block_id": f"paper-{processed_doc['paper_id']}-block-{order:04d}",
                        "order": order,
                        "block_type": "section_header",
                        "text": heading["full_heading"],
                        "page_start": page_number,
                        "page_end": page_number,
                        "section_heading": current_section_heading,
                        "section_path": current_section_path[:],
                        "approx_tokens": estimate_tokens(heading["full_heading"]),
                    }
                )
                order += 1
                continue

            block_type = classify_block_type(
                block_text=block_text,
                current_section_heading=current_section_heading,
            )

            blocks.append(
                {
                    "block_id": f"paper-{processed_doc['paper_id']}-block-{order:04d}",
                    "order": order,
                    "block_type": block_type,
                    "text": block_text,
                    "page_start": page_number,
                    "page_end": page_number,
                    "section_heading": current_section_heading,
                    "section_path": current_section_path[:],
                    "approx_tokens": estimate_tokens(block_text),
                }
            )
            order += 1

    return blocks


def blocks_to_segments(blocks: list[dict[str, Any]], max_segment_tokens: int) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []

    for block in blocks:
        if block["block_type"] == "section_header":
            continue

        pieces = split_long_text(block["text"], max_tokens=max_segment_tokens)
        for piece in pieces:
            segments.append(
                {
                    "block_type": block["block_type"],
                    "text": piece,
                    "page_start": block["page_start"],
                    "page_end": block["page_end"],
                    "section_heading": block["section_heading"],
                    "section_path": block["section_path"],
                    "approx_tokens": estimate_tokens(piece),
                }
            )

    return segments


def build_chunks_from_segments(
    segments: list[dict[str, Any]],
    paper_id: int,
    project_id: int,
    project_slug: str,
    min_chunk_tokens: int = 450,
    max_chunk_tokens: int = 650,
    overlap_tokens: int = 100,
) -> dict[str, Any]:
    if not segments:
        return {
            "paper_id": paper_id,
            "project_id": project_id,
            "project_slug": project_slug,
            "chunk_config": {
                "min_chunk_tokens": min_chunk_tokens,
                "max_chunk_tokens": max_chunk_tokens,
                "overlap_tokens": overlap_tokens,
            },
            "total_chunks": 0,
            "chunks": [],
        }

    chunks: list[dict[str, Any]] = []
    current_segments: list[dict[str, Any]] = []
    current_tokens = 0
    current_section_key: tuple | None = None

    def make_chunk(chunk_segments: list[dict[str, Any]], chunk_index: int) -> dict[str, Any]:
        first = chunk_segments[0]
        last = chunk_segments[-1]
        section_heading = first.get("section_heading")
        section_path = first.get("section_path") or []

        body = "\n\n".join(seg["text"] for seg in chunk_segments)
        if section_heading:
            chunk_text = f"{section_heading}\n\n{body}"
        else:
            chunk_text = body

        return {
            "chunk_id": f"paper-{paper_id}-chunk-{chunk_index:04d}",
            "chunk_index": chunk_index,
            "paper_id": paper_id,
            "project_id": project_id,
            "project_slug": project_slug,
            "page_start": first["page_start"],
            "page_end": last["page_end"],
            "section_heading": section_heading,
            "section_path": section_path,
            "block_types_in_chunk": sorted({seg["block_type"] for seg in chunk_segments}),
            "approx_tokens": estimate_tokens(chunk_text),
            "text": chunk_text,
        }

    def tail_overlap(chunk_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        token_total = 0

        for seg in reversed(chunk_segments):
            selected.append(seg)
            token_total += seg["approx_tokens"]
            if token_total >= overlap_tokens:
                break

        return list(reversed(selected))

    def flush_current_chunk(force_no_overlap: bool = False) -> None:
        nonlocal current_segments
        nonlocal current_tokens
        nonlocal current_section_key

        if not current_segments:
            return

        chunk_index = len(chunks)
        chunks.append(make_chunk(current_segments, chunk_index))

        if force_no_overlap:
            current_segments = []
            current_tokens = 0
            current_section_key = None
            return

        overlap = tail_overlap(current_segments)
        current_segments = overlap[:]
        current_tokens = sum(seg["approx_tokens"] for seg in current_segments)

    for seg in segments:
        section_key = (
            tuple(seg.get("section_path") or []),
            seg.get("section_heading"),
        )

        if current_segments and current_section_key != section_key:
            flush_current_chunk(force_no_overlap=True)

        if current_section_key is None:
            current_section_key = section_key

        if current_segments and current_tokens + seg["approx_tokens"] > max_chunk_tokens:
            flush_current_chunk(force_no_overlap=False)
            current_section_key = section_key

        current_segments.append(seg)
        current_tokens += seg["approx_tokens"]

    if current_segments:
        flush_current_chunk(force_no_overlap=True)

    return {
        "paper_id": paper_id,
        "project_id": project_id,
        "project_slug": project_slug,
        "chunk_config": {
            "min_chunk_tokens": min_chunk_tokens,
            "max_chunk_tokens": max_chunk_tokens,
            "overlap_tokens": overlap_tokens,
        },
        "total_chunks": len(chunks),
        "chunks": chunks,
    }


def chunk_processed_document(
    processed_doc: dict[str, Any],
    min_chunk_tokens: int = 450,
    max_chunk_tokens: int = 650,
    overlap_tokens: int = 100,
) -> dict[str, Any]:
    blocks = extract_blocks(processed_doc)

    segments = blocks_to_segments(
        blocks=blocks,
        max_segment_tokens=max(220, max_chunk_tokens // 2),
    )

    chunk_doc = build_chunks_from_segments(
        segments=segments,
        paper_id=processed_doc["paper_id"],
        project_id=processed_doc["project_id"],
        project_slug=processed_doc["project_slug"],
        min_chunk_tokens=min_chunk_tokens,
        max_chunk_tokens=max_chunk_tokens,
        overlap_tokens=overlap_tokens,
    )

    detected_sections = [
        block["text"] for block in blocks if block["block_type"] == "section_header"
    ]

    chunk_doc["source_processed_path"] = processed_doc.get("source_processed_path")
    chunk_doc["total_blocks"] = len(blocks)
    chunk_doc["detected_sections"] = detected_sections

    return chunk_doc

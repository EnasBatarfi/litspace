from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evaluation"

env_path = EVAL_DIR / ".env"
env_example_path = EVAL_DIR / ".env.example"
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    load_dotenv(env_example_path, override=True)

DATASET_CSV = EVAL_DIR / "datasets" / "questions.csv"
SUMMARIES_JSON = EVAL_DIR / "datasets" / "paper_summaries.json"
OUTPUTS_DIR = EVAL_DIR / "outputs"

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-5.4")
MAX_JUDGE_ATTEMPTS = 3
FAILURE_TYPES = {
    "wrong_paper",
    "missing_key_point",
    "unsupported_claim",
    "bad_followup",
    "over_clarification",
    "over_refusal",
    "should_have_clarified",
    "should_have_refused",
    "weak_evidence",
    "good",
}
REQUIRED_JUDGE_KEYS = {
    "correctness",
    "completeness",
    "relevance",
    "helpfulness",
    "faithfulness",
    "followup_success",
    "failure_type",
    "short_reason",
}


def load_questions() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with DATASET_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["turns_json"] = json.loads(row["turns_json"])
            row["expected_papers"] = [x for x in row["expected_papers"].split("|") if x]
            row["required_points"] = [x for x in row["required_points"].split("|") if x]
            row["should_clarify"] = str(row["should_clarify"]).strip() == "1"
            row["should_refuse"] = str(row["should_refuse"]).strip() == "1"
            rows[row["id"]] = row
    return rows


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_paper_summaries() -> dict:
    with SUMMARIES_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def format_summary_background(summaries: dict) -> str:
    lines = [
        "Benchmark paper summaries (background only; reference answer and required points override this map):"
    ]
    for paper, summary in summaries.items():
        goal = summary.get("goal", "")
        method = summary.get("method", "")
        lines.append(f"- {paper}: goal={goal} method={method}")
    return "\n".join(lines)


def format_litspace_sources(sources: list[dict]) -> str:
    if not sources:
        return "NONE"
    parts: list[str] = []
    for s in sources:
        parts.append(
            f"Paper: {s.get('paper_title', '')}\n"
            f"Section: {s.get('section_heading', '')}\n"
            f"Excerpt: {s.get('excerpt', '')}"
        )
    return "\n\n---\n\n".join(parts)


def build_prompt(qrow: dict, out_row: dict, system_type: str, summary_background: str) -> str:
    if system_type == "litspace":
        evidence = format_litspace_sources(out_row.get("used_sources", []))
        faithfulness_rule = (
            "Score faithfulness from 0 to 2 based on whether the answer is supported by the provided evidence."
        )
    elif system_type == "summary_few_shot":
        evidence = out_row.get("summary_context", "") or "NONE"
        faithfulness_rule = (
            "Score faithfulness from 0 to 2 based on whether the answer is supported by the provided summary context."
        )
    else:
        evidence = "NONE"
        faithfulness_rule = "Set faithfulness to null because this baseline had no document evidence."

    if qrow["should_clarify"]:
        expected_behavior = "clarify"
    elif qrow["should_refuse"]:
        expected_behavior = "refuse"
    else:
        expected_behavior = "answer"

    return f"""
{summary_background}

Question:
{qrow["question"]}

Turns:
{json.dumps(qrow["turns_json"], ensure_ascii=False)}

Expected papers:
{qrow["expected_papers"]}

Expected behavior:
{expected_behavior}

Reference answer:
{qrow["reference_answer"]}

Required points:
{qrow["required_points"]}

Evidence:
{evidence}

System answer:
{out_row["answer"]}

Scoring rubric:
- correctness:
  0 = materially wrong, off-paper, unsupported for the benchmark item, or fails the required behavior badly
  1 = partially correct but misses important distinctions, mixes correct content with doubtful claims, or only partly meets the required behavior
  2 = correct and well-aligned with the benchmark item

- completeness:
  0 = misses most required points
  1 = covers some required points but misses important ones
  2 = covers the main required points sufficiently

- relevance:
  0 = mostly off-topic or answers a different question
  1 = partly on-topic but unfocused, drifting, or weakly scoped
  2 = directly answers the asked question

- helpfulness:
  0 = not useful for this benchmark item
  1 = somewhat useful but weak, vague, or incomplete
  2 = clearly useful, appropriately scoped, and well-formed

- faithfulness:
  0 = unsupported by provided evidence/context
  1 = partly supported but includes extra unsupported detail
  2 = well-supported by provided evidence/context
  null = no evidence/context baseline

- followup_success:
  0 = loses the referent or behaves as if prior context was reset
  1 = partially preserves context but is incomplete, hesitant, or resolves scope weakly
  2 = correctly preserves and uses prior-turn context
  null = not a follow-up case

Behavior priority rules:
- If expected behavior is clarify, a short justified clarification is better than a confident unsupported direct answer.
- If expected behavior is refuse, a project-bounded refusal is better than an unsupported direct answer.
- If expected behavior is answer, unnecessary clarification should be treated as over_clarification.
- If expected behavior is answer, unnecessary refusal should be treated as over_refusal.
- For clarify or refuse rows, correctness and helpfulness should depend first on whether the system matched the expected behavior.

Support and overclaiming rules:
- Do not give extra credit merely because a system had more context.
- Judge the final answer's appropriateness for the benchmark item.
- If a no-context baseline sounds plausible but makes paper-specific claims it could not support from the prompt, penalize correctness/helpfulness and use unsupported_claim when appropriate.
- If the answer is broadly correct but includes extra unsupported specifics, do not automatically set correctness to 0.
- Prefer lowering faithfulness first for unsupported specifics.
- Use unsupported_claim when the core answer is mostly right but some details exceed the evidence.
- A cautious partial answer grounded in the provided evidence is better than an overconfident unsupported answer.

Additional rule:
{faithfulness_rule}

Return JSON with:
- correctness: 0, 1, or 2
- completeness: 0, 1, or 2
- relevance: 0, 1, or 2
- helpfulness: 0, 1, or 2
- faithfulness: 0, 1, or 2, or null
- followup_success: 0, 1, or 2, or null
- failure_type: one of ["wrong_paper","missing_key_point","unsupported_claim","bad_followup","over_clarification","over_refusal","should_have_clarified","should_have_refused","weak_evidence","good"]
- short_reason: string
""".strip()


def _validate_score(name: str, value: object) -> None:
    if value is None:
        return
    if value not in {0, 1, 2}:
        raise ValueError(f"{name} must be 0, 1, 2, or null")


def parse_judge_response(text: str) -> dict:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    missing = REQUIRED_JUDGE_KEYS - set(obj)
    if missing:
        raise ValueError(f"missing keys: {sorted(missing)}")

    for key in ("correctness", "completeness", "relevance", "helpfulness"):
        _validate_score(key, obj.get(key))

    _validate_score("faithfulness", obj.get("faithfulness"))
    _validate_score("followup_success", obj.get("followup_success"))

    if obj["failure_type"] not in FAILURE_TYPES:
        raise ValueError(f"invalid failure_type: {obj['failure_type']}")
    if not isinstance(obj["short_reason"], str) or not obj["short_reason"].strip():
        raise ValueError("short_reason must be a non-empty string")

    return obj


def request_judgment(
    client: OpenAI,
    *,
    judge_system: str,
    prompt: str,
    label: str,
) -> dict:
    last_error: str | None = None
    last_text = ""

    for attempt in range(1, MAX_JUDGE_ATTEMPTS + 1):
        response = client.responses.create(
            model=JUDGE_MODEL,
            input=[
                {"role": "system", "content": judge_system},
                {"role": "user", "content": prompt},
            ],
        )
        last_text = response.output_text.strip()
        try:
            return parse_judge_response(last_text)
        except ValueError as exc:
            last_error = str(exc)
            print(f"[evaluation] retry {label} attempt={attempt} reason={last_error}")

    raise RuntimeError(
        f"Judge returned invalid JSON for {label} after {MAX_JUDGE_ATTEMPTS} attempts: {last_error}\nRaw output: {last_text}"
    )


def judge_rows(
    client: OpenAI,
    questions: dict[str, dict],
    judge_system: str,
    summary_background: str,
    input_path: Path,
    output_path: Path,
    system_type: str,
    system_name: str,
) -> None:
    rows = read_jsonl(input_path)
    judged: list[dict] = []
    print(f"[evaluation] judging {system_name} from {input_path.name} with {len(rows)} rows")

    for row in rows:
        print(f"[evaluation] judge {system_name} {row['id']}")
        prompt = build_prompt(questions[row["id"]], row, system_type, summary_background)
        obj = request_judgment(
            client,
            judge_system=judge_system,
            prompt=prompt,
            label=f"{system_name}:{row['id']}",
        )
        obj["id"] = row["id"]
        obj["system_name"] = system_name
        judged.append(obj)

    write_jsonl(output_path, judged)
    print(f"[evaluation] wrote {output_path}")


def main() -> None:
    print("[evaluation] starting judge_answers")
    client = OpenAI(api_key=OPENAI_API_KEY)
    questions = load_questions()
    summary_background = format_summary_background(load_paper_summaries())

    judge_system = """You are a strict evaluator of a research-paper QA system.
Use only the provided question, turns, expected behavior, reference answer, required points, and evidence if given.
Do not use outside knowledge.
Use the summary background only as lightweight calibration context.
Reference answer and required points override the summary background if they conflict.
Return valid JSON only.
"""

    judge_rows(
        client=client,
        questions=questions,
        judge_system=judge_system,
        summary_background=summary_background,
        input_path=OUTPUTS_DIR / "litspace_outputs.jsonl",
        output_path=OUTPUTS_DIR / "judge_litspace.jsonl",
        system_type="litspace",
        system_name="litspace_rag",
    )
    judge_rows(
        client=client,
        questions=questions,
        judge_system=judge_system,
        summary_background=summary_background,
        input_path=OUTPUTS_DIR / "zero_shot_outputs.jsonl",
        output_path=OUTPUTS_DIR / "judge_zero_shot.jsonl",
        system_type="zero_shot",
        system_name="zero_shot",
    )
    judge_rows(
        client=client,
        questions=questions,
        judge_system=judge_system,
        summary_background=summary_background,
        input_path=OUTPUTS_DIR / "summary_few_shot_outputs.jsonl",
        output_path=OUTPUTS_DIR / "judge_summary_few_shot.jsonl",
        system_type="summary_few_shot",
        system_name="summary_few_shot",
    )
    print("[evaluation] judge_answers complete")


if __name__ == "__main__":
    main()

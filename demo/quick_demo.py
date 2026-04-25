from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
CORPUS_DIR = DEMO_DIR / "corpus"
EVAL_DIR = ROOT / "evaluation"
OUTPUTS_PATH = EVAL_DIR / "outputs" / "litspace_outputs.jsonl"
ENV_PATH = EVAL_DIR / ".env"
ENV_EXAMPLE_PATH = EVAL_DIR / ".env.example"
BACKEND_DIR = ROOT / "backend"

# Three representative prompts for the demo run.
DEMO_ITEMS = [
    {
        "id": "Q08",
        "title": "Single-paper summary",
        "prompt": "Summarize Progent in one short paragraph: goal, method, and main result.",
    },
    {
        "id": "Q15",
        "title": "Multi-paper comparison",
        "prompt": "What is the main difference between Progent and MCP-Secure in how they enforce runtime access control?",
    },
    {
        "id": "Q27",
        "title": "Evidence lookup",
        "prompt": "Which paper uses program dependence graphs to represent runtime traces?",
    },
]


def load_env_value(key: str) -> str | None:
    # Prefer values from the real environment, then fall back to the eval env files.
    if key in os.environ and os.environ[key].strip():
        return os.environ[key].strip()

    for path in (ENV_PATH, ENV_EXAMPLE_PATH):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            lhs, rhs = stripped.split("=", 1)
            if lhs.strip() == key and rhs.strip():
                return rhs.strip()
    return None


def load_static_outputs() -> dict[str, dict]:
    # Load the committed demo answers used for the static fallback mode.
    rows: dict[str, dict] = {}
    with OUTPUTS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def load_requests():
    # Keep the import local so the error message can point to the right Python env.
    try:
        import requests  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "This script needs the 'requests' package. Run it with backend/.litenv/bin/python."
        ) from exc
    return requests


def terminal_width() -> int:
    # Keep the terminal output readable without getting too wide.
    return max(72, min(108, shutil.get_terminal_size((96, 24)).columns))


def rule(char: str = "=") -> str:
    return char * terminal_width()


def print_section(title: str) -> None:
    # Top-level block heading for the demo output.
    print(rule())
    print(title)
    print(rule())


def print_subsection(title: str) -> None:
    # Smaller heading for each question block.
    print()
    print(title)
    print("-" * len(title))


def print_wrapped(label: str, text: str) -> None:
    # Wrap long lines so answers and status messages stay neat in the shell.
    width = terminal_width()
    wrapper = textwrap.TextWrapper(width=width, subsequent_indent=" " * (len(label) + 2))
    print(wrapper.fill(f"{label}: {text.strip()}"))


def format_api_error(response) -> str:
    # Pull the most useful error detail out of a backend response.
    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return f"HTTP {response.status_code}: {detail.strip()}"

    body = response.text.strip()
    if body:
        return f"HTTP {response.status_code}: {body}"
    return f"HTTP {response.status_code}"


def ensure_backend_running(session, api_base: str):
    # Reuse an existing backend if it is up; otherwise start a local one.
    health_url = f"{api_base.rstrip('/')}/health"

    try:
        response = session.get(health_url, timeout=3)
        response.raise_for_status()
        print_wrapped("Backend", "already running")
        print()
        return None
    except Exception:
        pass

    parsed = urlparse(api_base)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            f"Backend is not reachable at {api_base} and auto-start is only supported for localhost."
        )

    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000
    # Start the same backend app the frontend and evaluation scripts use.
    backend_command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    print_wrapped("Backend", "not running, starting it now")
    process = subprocess.Popen(
        backend_command,
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(30):
        try:
            response = session.get(health_url, timeout=3)
            response.raise_for_status()
            print_wrapped("Backend", f"started at {api_base}")
            print()
            return process
        except Exception:
            time.sleep(1)

    raise RuntimeError(f"Backend did not become ready at {api_base}")


def stop_backend(process) -> None:
    # Only stop the backend if this script started it.
    if process is None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
        print()
        print_wrapped("Backend", "stopped")
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        print()
        print_wrapped("Backend", "force-stopped")


def create_project(session, api_base: str, name: str) -> dict:
    # Create a temporary demo project in the running backend.
    response = session.post(
        f"{api_base}/projects",
        json={"name": name, "description": "Quick demo project seeded from demo/corpus"},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def create_chat(session, api_base: str, project_id: int, title: str = "Quick demo chat") -> dict:
    # Create one chat so all three demo questions land in the same thread.
    response = session.post(
        f"{api_base}/projects/{project_id}/chats",
        json={"title": title},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def delete_project(session, api_base: str, project_id: int) -> None:
    # Clean up the temporary project after the demo finishes.
    response = session.delete(f"{api_base}/projects/{project_id}", timeout=120)
    if response.status_code not in (200, 204):
        raise RuntimeError(format_api_error(response))


def upload_pdf(session, api_base: str, project_id: int, pdf_path: Path) -> int:
    # Upload one demo PDF and return its new paper id.
    with pdf_path.open("rb") as handle:
        response = session.post(
            f"{api_base}/projects/{project_id}/papers/upload",
            files={"file": (pdf_path.name, handle, "application/pdf")},
            timeout=300,
        )
    response.raise_for_status()
    payload = response.json()
    paper_id = payload.get("id")
    if paper_id is None:
        raise RuntimeError(
            f"Upload response for {pdf_path.name} did not include a paper id: {payload}"
        )
    return int(paper_id)


def parse_paper(session, api_base: str, paper_id: int) -> None:
    # Convert the uploaded PDF into the processed page format.
    response = session.post(f"{api_base}/papers/{paper_id}/parse", timeout=300)
    response.raise_for_status()


def chunk_paper(session, api_base: str, paper_id: int) -> None:
    # Split the processed paper into retrieval chunks.
    response = session.post(f"{api_base}/papers/{paper_id}/chunk", timeout=300)
    response.raise_for_status()


def index_project(session, api_base: str, project_id: int) -> dict:
    # Build the retrieval indexes for the whole demo project.
    response = session.post(f"{api_base}/projects/{project_id}/index", timeout=600)
    response.raise_for_status()
    return response.json()


def ask_project(session, api_base: str, project_id: int, chat_id: int | None, prompt: str) -> dict:
    # Send one question through the real answer endpoint.
    payload = {
        "query": prompt,
        "chat_id": chat_id,
        "top_k": int(load_env_value("LITSPACE_TOP_K") or "6"),
        "max_output_tokens": int(load_env_value("LITSPACE_MAX_OUTPUT_TOKENS") or "500"),
        "temperature": float(load_env_value("LITSPACE_TEMPERATURE") or "0.1"),
    }
    response = session.post(
        f"{api_base}/projects/{project_id}/ask",
        json=payload,
        timeout=180,
    )
    if not response.ok:
        raise RuntimeError(format_api_error(response))
    return response.json()


def print_answer_block(title: str, prompt: str, answer: str, sources: list[dict] | None) -> None:
    # Render one answer block in a clean terminal format.
    print_subsection(title)
    print_wrapped("Prompt", prompt)
    print()
    print(textwrap.fill(answer.strip(), width=terminal_width()))
    source_rows = sources or []
    if source_rows:
        top = source_rows[0]
        print()
        print_wrapped(
            "Top source",
            f"{top.get('paper_title') or top.get('original_filename')} | "
            f"section={top.get('section_heading')} | "
            f"pages={top.get('page_start')}-{top.get('page_end')}",
        )
    print()


def print_static_demo() -> None:
    # Fallback mode: show committed answers without touching the backend.
    rows = load_static_outputs()
    print_section("LitSpace Quick Demo")
    print_wrapped("Mode", "committed benchmark outputs")
    print_wrapped("Source", str(OUTPUTS_PATH.relative_to(ROOT)))
    print()

    for item in DEMO_ITEMS:
        row = rows[item["id"]]
        print_answer_block(
            title=f"{item['title']} ({item['id']})",
            prompt=item["prompt"],
            answer=row["answer"],
            sources=row.get("used_sources"),
        )


def seed_demo_project(session, api_base: str, project_name: str) -> dict:
    # Create a temporary project and load the seven demo papers into it.
    pdf_paths = sorted(CORPUS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise RuntimeError(f"No PDFs found in {CORPUS_DIR}")

    print_section("LitSpace Quick Demo")
    print_wrapped("Project", project_name)
    print_wrapped("Corpus", f"{len(pdf_paths)} PDFs from {CORPUS_DIR.relative_to(ROOT)}")
    print()

    project = create_project(session, api_base, project_name)
    project_id = int(project["id"])
    print_wrapped("Created", f"id={project_id} slug={project['slug']}")

    for index, pdf_path in enumerate(pdf_paths, start=1):
        # Run the same upload -> parse -> chunk flow the app normally uses.
        print(f"[{index}/{len(pdf_paths)}] upload  {pdf_path.name}")
        paper_id = upload_pdf(session, api_base, project_id, pdf_path)

        print(f"[{index}/{len(pdf_paths)}] parse   paper_id={paper_id}")
        parse_paper(session, api_base, paper_id)

        print(f"[{index}/{len(pdf_paths)}] chunk   paper_id={paper_id}")
        chunk_paper(session, api_base, paper_id)

    print()
    print_wrapped("Indexing", f"project {project_id}")
    index_info = index_project(session, api_base, project_id)
    print_wrapped(
        "Index ready",
        f"papers={index_info.get('total_indexed_papers')} chunks={index_info.get('total_chunks_indexed')}",
    )

    print()
    return project


def run_live_demo(session, api_base: str, project_id: int) -> None:
    # Ask the three demo questions against the freshly indexed project.
    chat = create_chat(session, api_base, project_id)
    chat_id = int(chat["id"])

    print_wrapped("Demo chat", f"project_id={project_id} chat_id={chat_id}")
    print_wrapped("LLM fallback", "handled by the backend if no GPT key is available")
    print()

    for item in DEMO_ITEMS:
        result = ask_project(session, api_base, project_id, chat_id, item["prompt"])
        print_answer_block(
            title=f"{item['title']} ({item['id']})",
            prompt=item["prompt"],
            answer=result.get("answer", ""),
            sources=result.get("used_sources"),
        )


def main() -> None:
    # Keep the CLI simple: normal live demo, or static fallback only.
    parser = argparse.ArgumentParser(
        description="Create a LitSpace demo project from demo/corpus and run three sample questions."
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Only print committed demo answers from evaluation/outputs/litspace_outputs.jsonl.",
    )
    args = parser.parse_args()

    if args.static:
        # Skip backend work completely and print the committed examples.
        print_static_demo()
        return

    requests = load_requests()
    api_base = load_env_value("LITSPACE_API_BASE")
    if not api_base:
        raise RuntimeError("Missing LITSPACE_API_BASE in evaluation/.env or the environment.")
    api_base = api_base.rstrip("/")

    session = requests.Session()
    backend_process = None
    created_project_id: int | None = None

    try:
        # Start the backend if needed, create the demo project, then run the questions.
        backend_process = ensure_backend_running(session, api_base)
        project = seed_demo_project(session, api_base, "LitSpace Quick Demo")
        project_id = int(project["id"])
        created_project_id = project_id

        try:
            run_live_demo(session, api_base, project_id)
        except Exception as exc:
            print_wrapped("Live demo failed", str(exc))
            print_wrapped("Fallback", "showing committed outputs instead")
            print()
            print_static_demo()
    finally:
        # Always clean up the temporary project and any backend started by this script.
        if created_project_id is not None:
            try:
                delete_project(session, api_base, created_project_id)
                print()
                print_wrapped("Cleanup", f"deleted demo project {created_project_id}")
            except Exception as exc:
                print()
                print_wrapped("Cleanup failed", f"could not delete project {created_project_id}: {exc}")
        stop_backend(backend_process)


if __name__ == "__main__":
    main()

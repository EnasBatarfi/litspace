from __future__ import annotations

import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evaluation"
CORPUS_DIR = EVAL_DIR / "corpus"
ENV_PATH = EVAL_DIR / ".env"


def load_eval_env() -> Path:
    source = ENV_PATH if ENV_PATH.exists() else EVAL_DIR / ".env.example"
    load_dotenv(source, override=False)
    return source


def update_env_value(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    replacement = f"{key}={value}"
    if pattern.search(text):
        text = pattern.sub(replacement, text)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += replacement + "\n"
    path.write_text(text, encoding="utf-8")


def create_project(session: requests.Session, api_base: str, name: str) -> dict:
    response = session.post(f"{api_base}/projects", json={"name": name}, timeout=120)
    response.raise_for_status()
    return response.json()


def upload_pdf(session: requests.Session, api_base: str, project_id: int, pdf_path: Path) -> int:
    with pdf_path.open("rb") as handle:
        response = session.post(
            f"{api_base}/projects/{project_id}/papers/upload",
            files={"file": (pdf_path.name, handle, "application/pdf")},
            timeout=300,
        )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        if payload.get("id") is not None:
            return int(payload["id"])
        if payload.get("paper_id") is not None:
            return int(payload["paper_id"])
        papers = payload.get("papers") or []
        if papers and papers[0].get("id") is not None:
            return int(papers[0]["id"])
    raise RuntimeError(f"Could not extract paper id from upload response for {pdf_path.name}: {payload}")


def parse_paper(session: requests.Session, api_base: str, paper_id: int) -> None:
    response = session.post(f"{api_base}/papers/{paper_id}/parse", timeout=300)
    response.raise_for_status()


def chunk_paper(session: requests.Session, api_base: str, paper_id: int) -> None:
    response = session.post(f"{api_base}/papers/{paper_id}/chunk", timeout=300)
    response.raise_for_status()


def index_project(session: requests.Session, api_base: str, project_id: int) -> None:
    response = session.post(f"{api_base}/projects/{project_id}/index", timeout=600)
    response.raise_for_status()


def main() -> None:
    env_source = load_eval_env()
    api_base = os.environ["LITSPACE_API_BASE"].rstrip("/")
    project_name = os.environ.get("EVAL_PROJECT_NAME", "LitSpace Eval")

    pdf_paths = sorted(CORPUS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise RuntimeError(f"No PDFs found in {CORPUS_DIR}")

    print(f"[evaluation] loaded environment from {env_source}")
    print(f"[evaluation] found {len(pdf_paths)} PDFs in {CORPUS_DIR}")

    session = requests.Session()
    project = create_project(session, api_base, project_name)
    project_id = int(project["id"])
    print(f"[evaluation] created fresh project '{project_name}' with id={project_id}")

    for index, pdf_path in enumerate(pdf_paths, start=1):
        print(f"[evaluation] [{index}/{len(pdf_paths)}] uploading {pdf_path.name}")
        paper_id = upload_pdf(session, api_base, project_id, pdf_path)

        print(f"[evaluation] [{index}/{len(pdf_paths)}] parsing paper_id={paper_id}")
        parse_paper(session, api_base, paper_id)

        print(f"[evaluation] [{index}/{len(pdf_paths)}] chunking paper_id={paper_id}")
        chunk_paper(session, api_base, paper_id)

    print(f"[evaluation] indexing project_id={project_id}")
    index_project(session, api_base, project_id)

    update_env_value(ENV_PATH, "LITSPACE_EVAL_PROJECT_ID", str(project_id))
    print(f"[evaluation] updated {ENV_PATH}")

    print("[evaluation] setup complete")
    print(f"[evaluation] project_id={project_id}")


if __name__ == "__main__":
    main()

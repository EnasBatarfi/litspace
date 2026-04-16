# LitSpace

LitSpace is a grounded multi-paper research workspace for academic PDFs.

## Stack

- Frontend: Next.js
- Backend: FastAPI
- PDF parsing: PyMuPDF
- Vector store: Chroma
- Embeddings: Sentence Transformers
- Retrieval: Hybrid retrieval with reranking
- Data storage: Local files + SQLite

## Goals

- Project-scoped PDF upload
- Single-paper and multi-paper QA
- Summaries
- Comparison
- Evidence lookup
- Strong grounding and citations

## Project Progress

### Phase 1. Persistent Project And Paper Foundation

1. [x] Create monorepo structure.
2. [x] Initialize FastAPI backend.
3. [x] Use Python 3.11 backend virtual environment with `.litenv`.
4. [x] Install backend dependencies.
5. [x] Add environment config files.
6. [x] Add root `.gitignore`.
7. [x] Add data folders with `.gitkeep` files.
8. [x] Add health endpoint.
9. [x] Add project and paper SQLAlchemy models.
10. [x] Add SQLite session and database startup setup.
11. [x] Add project schemas.
12. [x] Add slug and path helper utilities.
13. [x] Add `POST /projects`.
14. [x] Add `GET /projects`.
15. [x] Add `GET /projects/{id}`.
16. [x] Store created projects in SQLite.
17. [x] Create matching project folders under `data/raw/`, `data/processed/`, and `data/indexes/`.

Primary files/directories touched:

- `backend/requirements.txt`
- `backend/.env.example`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/models/project.py`
- `backend/app/models/paper.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/project.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/projects.py`
- `backend/app/utils/slug.py`
- `backend/app/utils/paths.py`
- `data/raw/.gitkeep`
- `data/processed/.gitkeep`
- `data/indexes/.gitkeep`
- `data/eval/.gitkeep`

### Phase 2. PDF Upload Flow

1. [x] Upload PDFs into a selected project.
2. [x] Save raw PDFs under project folders.
3. [x] Create paper records in SQLite.
4. [x] List papers per project.
5. [x] Use readable project-local stored filenames.

Primary files/directories touched:

- `backend/app/api/routes/upload.py`
- `backend/app/api/routes/projects.py`
- `backend/app/api/router.py`
- `backend/app/services/storage.py`
- `backend/app/schemas/paper.py`
- `backend/app/models/paper.py`
- `backend/app/utils/paths.py`
- `backend/app/utils/slug.py`
- `data/raw/<project-slug>/`
- `data/litspace.db`

Uploaded PDFs are stored as:

```text
data/raw/<project-slug>/<cleaned-original-filename>.pdf
```

If a filename already exists in the same project, LitSpace appends `-2`, `-3`, and so on.

Example:

```text
data/raw/llm-isolation-privacy/llm-paper-1.pdf
```

### Phase 3. Parsing Pipeline

1. [x] Parse PDFs with PyMuPDF.
2. [x] Extract page-level structured text.
3. [x] Save parsed JSON under `data/processed/`.
4. [x] Update paper parsing status from `uploaded` to `parsed`.
5. [x] Add `POST /papers/{paper_id}/parse`.
6. [x] Store predictable processed document paths.

Primary files/directories touched:

- `backend/app/api/routes/parsing.py`
- `backend/app/api/router.py`
- `backend/app/services/parsing/pdf_parser.py`
- `backend/app/services/parsing/document_store.py`
- `backend/app/models/paper.py`
- `backend/app/schemas/paper.py`
- `backend/app/utils/paths.py`
- `data/processed/<project-slug>/<paper-id>.json`
- `data/litspace.db`

Processed documents are stored as:

```text
data/processed/<project-slug>/<paper-id>.json
```

Example:

```text
data/processed/llm-isolation-privacy/1.json
```

The processed JSON includes paper metadata, source PDF path, total page count, and page-level extracted text.

### Phase 4. Chunking Pipeline

1. [x] Add lightweight structure-aware chunking.
2. [x] Add fallback splitting for long extracted blocks.
3. [x] Store chunk metadata with page, section, and block-type info.
4. [x] Save chunk JSON under `data/processed/`.
5. [x] Add `POST /papers/{paper_id}/chunk`.
6. [x] Update paper status from `parsed` to `chunked`.

Primary files/directories touched:

- `backend/app/api/routes/chunking.py`
- `backend/app/api/router.py`
- `backend/app/services/chunking/chunker.py`
- `backend/app/utils/paths.py`
- `backend/app/services/parsing/document_store.py`
- `data/processed/<project-slug>/<paper-id>.chunks.json`
- `data/litspace.db`

Chunk documents are stored as:

```text
data/processed/<project-slug>/<paper-id>.chunks.json
```

Example:

```text
data/processed/llm-isolation-privacy/1.chunks.json
```

The chunk JSON includes paper metadata, chunk configuration, total chunk count, chunk text, page ranges, section headings, section paths, block types, and detected sections.

The chunker is intentionally heuristic and lightweight. It uses PyMuPDF-extracted page text, line-level block reconstruction, numbered heading detection, appendix heading detection, first-page title merging, and section-bounded overlap. References are treated as normal paper content and are not excluded from later indexing.

Known limitations:

- Section detection is heuristic, not a full layout parser.
- Figures, tables, and diagram labels remain mixed into normal text chunks.
- Some inline subsection labels may remain inside paragraph text instead of becoming standalone sections.
- PDFs with unusual formatting, scanned pages, or broken text extraction may still need OCR or richer PyMuPDF layout metadata.
- First-page title and appendix handling are best-effort rules designed for academic papers, not guaranteed for every publisher template.

### Phase 5. Indexing Pipeline

1. [ ] Add local embedding model.
2. [ ] Add Chroma vector index.
3. [ ] Add BM25 lexical index.
4. [ ] Build project-scoped indexing.

Primary files/directories touched:

- Not implemented yet.
- Expected touch points: `backend/app/api/routes/indexing.py`, `backend/app/services/indexing/`, and `data/indexes/<project-slug>/`.

### Phase 6. Query And Grounded Generation

1. [ ] Add semantic-only baseline retrieval.
2. [ ] Add hybrid retrieval.
3. [ ] Add reranking.
4. [ ] Add grounded prompt templates.
5. [ ] Return citations.
6. [ ] Add abstention behavior.

Primary files/directories touched:

- Not implemented yet.
- Expected touch points: `backend/app/api/routes/query.py`, retrieval services, prompt-building services, and frontend query UI files.

### Phase 7. Evaluation Harness

1. [ ] Build gold question set.
2. [ ] Add retrieval metrics.
3. [ ] Add answer quality metrics.
4. [ ] Add error analysis labels.
5. [ ] Compare no-RAG vs RAG baseline.
6. [ ] Compare semantic vs hybrid retrieval.
7. [ ] Compare no-reranker vs reranker.

Primary files/directories touched:

- Not implemented yet.
- Expected touch points: `data/eval/`, evaluation scripts/services, and retrieval result artifacts.

### Phase 8. Thin UI Polish

1. [x] Initialize Next.js frontend.
2. [x] Add frontend API client.
3. [ ] Add simple project page.
4. [ ] Add simple upload page.
5. [ ] Add simple query page.
6. [ ] Add evidence panel.

Primary files/directories touched:

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/pnpm-lock.yaml`
- `frontend/next.config.ts`
- `frontend/tsconfig.json`
- `frontend/eslint.config.mjs`
- `frontend/postcss.config.mjs`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/lib/api.ts`
- `frontend/public/`

## Local development

### Backend

```bash
cd backend
python3.11 -m venv .litenv
source .litenv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

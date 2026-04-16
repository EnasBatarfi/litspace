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

### Phase 2. PDF Upload Flow

1. [x] Upload PDFs into a selected project.
2. [x] Save raw PDFs under project folders.
3. [x] Create paper records in SQLite.
4. [x] List papers per project.
5. [x] Use readable project-local stored filenames.

Uploaded PDFs are stored as:

```text
data/raw/<project-slug>/<cleaned-original-filename>.pdf
```

If a filename already exists in the same project, LitSpace appends `-2`, `-3`, and so on.

Example:

```text
data/raw/llm-isolation-privacy/exam2-concept-by-concept-practice-copy-2.pdf
```

### Phase 3. Parsing Pipeline

1. [ ] Parse PDFs with PyMuPDF.
2. [ ] Extract page-level structured text.
3. [ ] Save parsed JSON under `data/processed/`.
4. [ ] Update paper parsing status.

### Phase 4. Chunking Pipeline

1. [ ] Add structure-aware chunking.
2. [ ] Add fallback chunking.
3. [ ] Store chunk metadata with page and section info.
4. [ ] Save chunk JSON.

### Phase 5. Indexing Pipeline

1. [ ] Add local embedding model.
2. [ ] Add Chroma vector index.
3. [ ] Add BM25 lexical index.
4. [ ] Build project-scoped indexing.

### Phase 6. Query And Grounded Generation

1. [ ] Add semantic-only baseline retrieval.
2. [ ] Add hybrid retrieval.
3. [ ] Add reranking.
4. [ ] Add grounded prompt templates.
5. [ ] Return citations.
6. [ ] Add abstention behavior.

### Phase 7. Evaluation Harness

1. [ ] Build gold question set.
2. [ ] Add retrieval metrics.
3. [ ] Add answer quality metrics.
4. [ ] Add error analysis labels.
5. [ ] Compare no-RAG vs RAG baseline.
6. [ ] Compare semantic vs hybrid retrieval.
7. [ ] Compare no-reranker vs reranker.

### Phase 8. Thin UI Polish

1. [x] Initialize Next.js frontend.
2. [x] Add frontend API client.
3. [ ] Add simple project page.
4. [ ] Add simple upload page.
5. [ ] Add simple query page.
6. [ ] Add evidence panel.

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

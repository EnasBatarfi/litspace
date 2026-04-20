# LitSpace

LitSpace is a grounded multi-paper research workspace for academic PDFs.

## Stack

- Frontend: Next.js
- Backend: FastAPI
- PDF parsing: PyMuPDF
- Vector store: Chroma
- Embeddings: Sentence Transformers
- Retrieval: Hybrid semantic and lexical retrieval with reciprocal rank fusion
- Generation: Local Ollama chat model
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

1. [x] Add local embedding model with Sentence Transformers.
2. [x] Add Chroma semantic vector index.
3. [x] Add BM25 lexical index payload.
4. [x] Build project-scoped indexing across all chunked papers.
5. [x] Add `POST /projects/{project_id}/index`.
6. [x] Update indexed paper statuses from `chunked` to `indexed`.

Primary files/directories touched:

- `backend/requirements.txt`
- `backend/app/core/config.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/indexing.py`
- `backend/app/schemas/indexing.py`
- `backend/app/services/embedding/encoder.py`
- `backend/app/services/indexing/chroma_indexer.py`
- `backend/app/services/indexing/bm25_indexer.py`
- `backend/app/utils/paths.py`
- `data/indexes/chroma/`
- `data/indexes/<project-slug>/bm25.json`
- `data/litspace.db`

Project indexes are stored as:

```text
data/indexes/chroma/
data/indexes/<project-slug>/bm25.json
```

Example:

```text
data/indexes/chroma/chroma.sqlite3
data/indexes/llm-isolation-privacy/bm25.json
```

The indexing endpoint reads all chunk files for a project, embeds each chunk with the configured embedding model, recreates the project's Chroma collection, writes a BM25 payload, and marks successfully indexed papers as `indexed`.

Indexing response fields include project metadata, indexed paper IDs, total chunks indexed, embedding model, Chroma collection name, and BM25 index path.

Current validation for `llm-isolation-privacy`: 3 papers indexed, 166 chunks indexed, Chroma persisted on disk, BM25 JSON built, and all 3 papers marked `indexed`.

Known limitations:

- Indexing is ingestion-only; evidence retrieval is handled in Phase 6 and answer generation is handled in Phase 7.
- Re-indexing currently recreates the full project Chroma collection instead of incrementally updating changed papers.
- The BM25 file stores tokenized entries as JSON for simple local retrieval, not a compact production search index.
- First-time embedding may require model download and can be slow.
- Apple MPS acceleration is best-effort; the embedding service can fall back to CPU if MPS causes runtime issues.

### Phase 6. Retrieval And Evidence Pipeline

1. [x] Add semantic retrieval from Chroma.
2. [x] Add lexical retrieval from BM25.
3. [x] Merge semantic and lexical hits with reciprocal rank fusion.
4. [x] Return top evidence chunks with chunk text and metadata.
5. [x] Add `POST /projects/{project_id}/retrieve`.
6. [x] Keep retrieval scoped to the selected project.
7. [ ] Add reranking after baseline retrieval quality is reviewed.

Primary files/directories touched:

- `backend/app/api/router.py`
- `backend/app/api/routes/query.py`
- `backend/app/schemas/retrieval.py`
- `backend/app/services/retrieval/chroma_retriever.py`
- `backend/app/services/retrieval/bm25_retriever.py`
- `backend/app/services/retrieval/hybrid.py`
- `backend/app/services/embedding/encoder.py`
- `backend/app/services/indexing/chroma_indexer.py`
- `backend/app/services/indexing/bm25_indexer.py`
- `data/indexes/chroma/`
- `data/indexes/<project-slug>/bm25.json`

The retrieval endpoint accepts a project-scoped query and returns evidence chunks only:

```text
POST /projects/{project_id}/retrieve
```

Example request:

```json
{
  "query": "How does Progent enforce privilege control over tool calls?",
  "top_k": 5
}
```

Each hit includes chunk ID, paper ID, project metadata, chunk index, page range, section heading, paper title, original filename, chunk text, semantic rank, lexical rank, and hybrid score.

Current validation queries:

- Progent privilege control query returns relevant Progent chunks from paper 1.
- Sesame policy container query returns relevant Sesame chunks from paper 3.
- Broad LLM-agent attack-vector query returns relevant security chunks, mostly from Progent.
- Sesame runtime overhead query returns Sesame performance chunks, with one related CSAgent overhead hit.

Known limitations:

- Retrieval returns evidence chunks only; grounded answer generation is handled separately in Phase 7.
- Hybrid ranking currently uses reciprocal rank fusion without learned weighting or reranking.
- BM25 is rebuilt from the JSON payload at retrieval time, which is simple but not optimized for large corpora.
- Reference sections and noisy chunks are not filtered out yet.
- Retrieval quality still needs tuning after more query coverage, especially for broad multi-paper questions.

### Phase 7. Grounded Answer Generation

1. [x] Add local LLM generation config for Ollama.
2. [x] Add grounded ask schemas.
3. [x] Factor shared hybrid retrieval pipeline for `/retrieve` and `/ask`.
4. [x] Add grounded prompt templates over retrieved chunks.
5. [x] Add local Ollama chat client.
6. [x] Add answer orchestration service.
7. [x] Add `POST /projects/{project_id}/ask`.
8. [x] Return answers with inline source tags like `[S1]`.
9. [x] Return supporting source snippets used by the answer.
10. [x] Return cautious insufficient-evidence answers for unsupported questions.
11. [x] Ensure insufficient-evidence responses return `used_sources: []`.

Primary files/directories touched:

- `backend/requirements.txt`
- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/query.py`
- `backend/app/api/routes/answering.py`
- `backend/app/schemas/answering.py`
- `backend/app/services/retrieval/pipeline.py`
- `backend/app/services/generation/prompting.py`
- `backend/app/services/llm/client.py`
- `backend/app/services/answering/answerer.py`

The ask endpoint retrieves evidence from the selected project, sends only those chunks to the configured local model, and returns a grounded answer plus the source excerpts:

```text
POST /projects/{project_id}/ask
```

Example request:

```json
{
  "query": "How does Progent enforce privilege control over tool calls?",
  "top_k": 5,
  "max_output_tokens": 400,
  "temperature": 0.1
}
```

Each response includes the project ID, project slug, original query, answer text, `insufficient_evidence`, retrieval hit count, and `used_sources`.

Current validation:

- Supported Progent questions return grounded answers with inline citations.
- Supported Sesame definition questions return grounded answers with inline citations.
- Obviously unsupported questions return a cautious insufficient-evidence answer instead of a world-knowledge answer.
- Insufficient-evidence answers return an empty `used_sources` list.

Known limitations:

- This is grounded QA only; summary, compare, and richer answer modes are not implemented yet.
- Answer quality depends on retrieval quality. If retrieval selects the wrong paper, generation can still answer from the wrong evidence.
- Typo-heavy metadata queries, such as misspelled paper names or author lookups, are weak because retrieval is optimized for chunked content QA rather than normalized metadata search.
- Broad ambiguous terms like "threat model" may retrieve the wrong paper when multiple papers use similar language.
- The unsupported-question guard is heuristic and should be evaluated systematically in Phase 8.

### Phase 8. Evaluation Harness

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

### Phase 9. Thin UI Polish

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

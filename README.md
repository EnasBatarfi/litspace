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

## Recent Improvements

- Added lightweight clarification continuation so short follow-ups like `first`, `third`, `1`, `paper 2`, and `first and second` reuse the prior summarize or compare intent instead of forcing the user to restate the full request.
- Added natural selected-paper defaults:
  - one selected paper can drive `summarize`, `explain`, or similar singular follow-ups
  - multiple selected papers can drive `compare`, `summarize the papers`, and similar plural follow-ups
- Improved comparison resolution so prompts like `compare`, `compare them`, `compare first and second`, and `compare with <paper>` compose selected scope, explicit paper mentions, and recent clarified scope more naturally.
- Summary and comparison requests now prefer clarification or partial grounded answers instead of failing early with blanket insufficient-evidence responses.
- Evidence requests remain stricter than summary and compare flows, but now report partial support when only some papers or claims are backed by retrieved evidence.
- Added project-bounded discovery behavior for prompts like `which paper mentions X` and `search ... in all papers`, instead of treating them like open-domain chat or generic help openings.
- Tightened ask routing so project-scoped identification questions like `which paper focuses on ...` are answered directly, while truly ambiguous prompts still clarify.
- Added explicit project-bounded refusals for out-of-domain questions instead of routing them through vague insufficient-evidence replies.
- The ask API now returns an `action` label (`answer`, `clarify`, or `refuse`) alongside the grounded answer payload.
- Added lightweight continuation for assistant-offered follow-ups such as `yes`, `yes do it`, and `do it`, so quote-pull and similar multi-turn actions continue naturally.
- Reduced repetitive low-value unsupported addenda so supported answers read more cleanly.
- Simplified the papers rail UI:
  - left-side checkbox for selection
  - simpler header copy
  - lighter card styling with less visual noise
  - papers remain shared across chats within the same project

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

Each response includes the project ID, project slug, original query, answer text, `action`, `insufficient_evidence`, retrieval hit count, `used_sources`, and optional timing / usage metadata.

Current validation:

- Supported Progent questions return grounded answers with inline citations.
- Supported Sesame definition questions return grounded answers with inline citations.
- Obviously unsupported questions return a cautious insufficient-evidence answer instead of a world-knowledge answer.
- Clearly out-of-project questions return an explicit project-bounded refusal.
- Insufficient-evidence answers return an empty `used_sources` list.

Known limitations:

- Summary, compare, explain, discovery, and evidence requests are all routed through the same grounded `/ask` flow rather than separate dedicated APIs.
- Answer quality depends on retrieval quality. If retrieval selects the wrong paper, generation can still answer from the wrong evidence.
- Typo-heavy metadata queries, such as misspelled paper names or author lookups, are weak because retrieval is optimized for chunked content QA rather than normalized metadata search.
- Broad ambiguous terms like "threat model" may retrieve the wrong paper when multiple papers use similar language.
- The unsupported-question guard is heuristic and should be evaluated systematically in Phase 8.

### Phase 8. Evaluation Harness

1. [x] Build a starter gold-question CSV template.
2. [x] Add retrieval metrics aggregation and manual retrieval-label sheets.
3. [x] Add answer quality judging with an LLM judge harness.
4. [x] Add error analysis exports.
5. [x] Add no-RAG vs RAG baseline evaluation harness.

Primary files/directories touched:

- `evaluation/scripts/`
- `evaluation/datasets/questions.csv`
- `evaluation/`

What the evaluation harness is:

- It is the benchmark pipeline for LitSpace, not part of the main product runtime.
- It runs the benchmark questions against LitSpace and the baselines.
- It stores the raw answers.
- It asks a judge model to score those answers.
- It aggregates the scores into summary metrics and pairwise comparisons.

In short, the flow is:

```text
evaluation/datasets/questions.csv
-> run systems
-> write raw outputs
-> judge answers
-> summarize metrics
```

Main entrypoints:

- `evaluation/scripts/run_systems.py`
- `evaluation/scripts/judge_answers.py`
- `evaluation/scripts/pairwise_judge.py`
- `evaluation/scripts/summarize_results.py`

Current evaluation artifacts:

- `evaluation/datasets/questions.csv`
  Benchmark questions, expected behavior, reference answers, and required points.
- `evaluation/outputs/`
  Raw answers from LitSpace and baselines, plus raw judge outputs.
- `evaluation/results/`
  Aggregated metrics, summaries, and error-analysis files.

The starter question set lives under `evaluation/datasets/` and is meant to be completed with reference answers and required points before running the judge.

### Phase 9. Thin UI Polish

1. [x] Initialize Next.js frontend.
2. [x] Add frontend API client.
3. [x] Replace the placeholder page with a project workspace shell.
4. [x] Add project creation, project listing, and project-scoped selection in the UI.
5. [x] Add project papers panel and evidence panel.
6. [x] Add a grounded chat composer wired to the backend ask flow.
7. [x] Add a reusable component structure for the workspace shell.

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
- `frontend/src/components/litspace/`
- `frontend/public/`

### Phase 10. Persistent Workspace UX And Backend Wiring

1. [x] Add backend chat and message models with project-linked chat persistence.
2. [x] Add `POST /projects/{project_id}/chats`.
3. [x] Add `GET /projects/{project_id}/chats`.
4. [x] Add `GET /chats/{chat_id}`.
5. [x] Add `DELETE /chats/{chat_id}`.
6. [x] Extend `POST /projects/{project_id}/ask` to accept an optional `chat_id`.
7. [x] Persist user and assistant turns into chat history.
8. [x] Update chat titles from the first real user turn instead of creating a new chat for every question.
9. [x] Add real project delete support with index and directory cleanup.
10. [x] Add real paper delete support with file cleanup and project index resync.
11. [x] Add project index synchronization helpers so delete and reindex flows rebuild Chroma and BM25 consistently.
12. [x] Make semantic and lexical retrieval return empty hits cleanly when a project has no current indexes.
13. [x] Normalize grouped citations like `[S1, S2]` into separate tags and keep prompt instructions consistent with separate citations.
14. [x] Wire frontend upload to the full pipeline: upload, parse, chunk, then project reindex.
15. [x] Replace the placeholder frontend with a real project workspace:
    - nested project/chat sidebar
    - project-scoped papers panel
    - grounded chat thread
    - sources panel driven by answer citations
16. [x] Add frontend project creation modal and project-scoped `New Chat` behavior.
17. [x] Add frontend delete confirmations for project, chat, and paper actions.
18. [x] Keep citations clickable and open/focus the matching source card in the right panel without reordering the full source list.
19. [x] Add collapsible papers and sources rails and expand the main chat area when they are closed.
20. [x] Remove dead or fake controls so only wired actions remain interactive.

Primary files/directories touched:

Backend:

- `backend/app/api/router.py`
- `backend/app/api/routes/answering.py`
- `backend/app/api/routes/chats.py`
- `backend/app/api/routes/indexing.py`
- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/upload.py`
- `backend/app/models/chat.py`
- `backend/app/models/message.py`
- `backend/app/models/project.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/answering.py`
- `backend/app/schemas/chat.py`
- `backend/app/services/answering/answerer.py`
- `backend/app/services/generation/prompting.py`
- `backend/app/services/indexing/chroma_indexer.py`
- `backend/app/services/indexing/project_index_manager.py`
- `backend/app/services/retrieval/chroma_retriever.py`
- `backend/app/services/retrieval/bm25_retriever.py`
- `backend/app/utils/paths.py`

Frontend:

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/pnpm-lock.yaml`
- `frontend/next.config.ts`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/lib/api.ts`
- `frontend/src/components/litspace/AppSidebar.tsx`
- `frontend/src/components/litspace/ChatInputBar.tsx`
- `frontend/src/components/litspace/ChatThread.tsx`
- `frontend/src/components/litspace/CreateProjectModal.tsx`
- `frontend/src/components/litspace/DeleteItemModal.tsx`
- `frontend/src/components/litspace/PapersPanel.tsx`
- `frontend/src/components/litspace/QuickActionsBar.tsx`
- `frontend/src/components/litspace/SourcesPanel.tsx`
- `frontend/src/components/litspace/WorkspaceHeader.tsx`
- `frontend/src/components/litspace/WorkspaceShell.tsx`
- `frontend/src/components/litspace/types.ts`

Current workspace behavior after these changes:

- Projects are the top-level unit.
- Chats are persisted inside projects and survive refresh.
- Papers remain project-scoped and shared across chats in the same project.
- Uploading from the UI now runs the full ingestion pipeline instead of stopping at raw upload.
- Deleting a paper removes its files and refreshes project indexes.
- Deleting a project removes the project row, linked chats/messages, vector index collection, BM25 payload, and local project directories.
- The ask flow can either remain backward compatible without a chat ID or append a multi-turn conversation to an existing chat.
- The sources panel is driven by citations in the current answer rather than duplicated source cards under each response.

Known limitations after this phase:

- Chat persistence uses new `chats` and `messages` tables, so existing deployments need the backend to restart and create those tables before the full workspace flow is available.
- `summary`, `compare`, and other quick actions still share the same backend ask pipeline rather than using separate dedicated endpoints.
- There is still no authenticated multi-user model; all projects remain local single-user workspace data.

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

### Evaluation Harness

The evaluation harness uses the existing HTTP API as a black-box and writes artifacts under `evaluation/`.

What it does:

1. `run_systems.py` runs LitSpace and the baselines on every benchmark row.
2. `judge_answers.py` scores each system answer with an LLM judge.
3. `pairwise_judge.py` compares LitSpace head-to-head against each baseline.
4. `summarize_results.py` turns those outputs into final metrics and result tables.

The key folders are:

- `evaluation/datasets/`: benchmark inputs
- `evaluation/outputs/`: raw system and judge outputs
- `evaluation/results/`: final summaries

Set these environment variables before running it:

```bash
export LITSPACE_API_BASE=http://127.0.0.1:8000
export LITSPACE_EVAL_PROJECT_ID=<project-id>
export OPENAI_API_KEY=<your-openai-key>
```

Useful commands:

```bash
backend/.litenv/bin/python evaluation/scripts/setup_project.py
backend/.litenv/bin/python evaluation/scripts/run_systems.py
backend/.litenv/bin/python evaluation/scripts/judge_answers.py
backend/.litenv/bin/python evaluation/scripts/pairwise_judge.py
backend/.litenv/bin/python evaluation/scripts/summarize_results.py
```

Notes:

- `setup_project.py` is optional if you already have an evaluation project created and indexed.
- `run_systems.py` writes raw system answers into `evaluation/outputs/`.
- `judge_answers.py` and `pairwise_judge.py` require `OPENAI_API_KEY`.
- `summarize_results.py` writes final summaries into `evaluation/results/`.

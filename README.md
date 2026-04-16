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

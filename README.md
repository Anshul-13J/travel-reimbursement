# Travel Reimbursement Approval Agent

POC for an AI-powered travel expense reimbursement workflow built with FastAPI, LangGraph, and Streamlit.

## Architecture

```
Streamlit Frontend
        │
        ▼
FastAPI Backend  (backend/api.py)
        │
        ▼
LangGraph Workflow  (agent/workflow.py)
  ┌─────────────────────────────────────┐
  │ 1. normalize_claim                  │
  │ 2. retrieve_policy_context (Chroma) │
  │ 3. run_rule_checks                  │
  │    - receipt_validator              │
  │    - duplicate_detector             │
  │    - limit_checker                  │
  │    - approval_checker               │
  │ 4. detect_clarification_need        │
  │ 5. generate_clarification_questions │  ← stops here if needed
  │ 6. decision_agent (Groq LLM)        │
  │ 7. validate_decision_output         │
  └─────────────────────────────────────┘
        │
        ▼
   OCR Service (PaddleOCR + local Ollama)
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### 3. Build the ChromaDB policy index (once)

```bash
python rag/build_index.py
```

Requires Ollama running with `nomic-embed-text` model pulled.

### 4. Start the backend

```bash
cd backend
uvicorn api:app --reload --port 8000
```

### 5. Start the frontend

```bash
streamlit run frontend/streamlit_app.py
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/groq/health` | Groq LLM connectivity check |
| POST | `/ocr` | Extract and parse a receipt image |
| POST | `/submit` | Submit a claim for processing |
| POST | `/claims/{id}/answers` | Submit clarification answers |
| GET | `/claims/{id}` | Get claim state |

## Models used

| Purpose | Model | Provider |
|---|---|---|
| OCR parsing | gemma3:4b | Ollama (local) |
| Policy embeddings | nomic-embed-text | Ollama (local) |
| Decision making | llama-3.3-70b-versatile | Groq API |

## Policy retrieval

Policies are stored as Markdown in `policies/`. Run `rag/build_index.py` to index them into ChromaDB (`vectorDB/chroma`). The workflow falls back to keyword search if ChromaDB is unavailable.







  Streamlit Frontend
                            |
                            v
                    Python Backend API
                            |
            +---------------+----------------+
            |                                |
            v                                v
        OCR Service                    n8n Workflow
            |                                |
            +---------------+----------------+
                            |
                            v
                    Decision Agent
                            |
                            v
                    Structured Output



PaddleOCR
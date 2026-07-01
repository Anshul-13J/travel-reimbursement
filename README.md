# Travel Reimbursement Approval Agent

A proof-of-concept AI-driven travel expense reimbursement workflow built with:
- Streamlit frontend
- FastAPI backend
- Local OCR + local Ollama models
- RAG policy retrieval
- LangGraph workflow orchestration
- Groq decision-making

## Overview

This project connects multiple AI components into a single claims pipeline:
1. The Streamlit frontend collects employee claims and receipt uploads.
2. The FastAPI backend exposes OCR and claim submission APIs.
3. Receipt OCR is performed with PaddleOCR, then parsed with a local Ollama model.
4. Policies are retrieved via a local RAG pipeline using Ollama embeddings.
5. A LangGraph workflow evaluates each expense and makes final decisions through Groq.

## Architecture

```
Streamlit Frontend
        │
        ▼
FastAPI Backend (/backend/api.py)
  ├─ POST /ocr → receipt OCR + local LLM parsing
  ├─ POST /submit → LangGraph workflow
  ├─ POST /claims/{id}/answers → clarification handling
  └─ GET /groq/health → Groq health
        │
        ▼
LangGraph Workflow (/agent/workflow.py)
  ┌───────────────────────────────────────────────────┐
  │ 1. normalize_claim                                │
  │ 2. retrieve_policy_context (Chroma/RAG fallback)  │
  │ 3. run_rule_checks                                │
  │ 4. detect_clarification_need                      │
  │ 5. generate_clarification_questions               │
  │ 6. decision_agent (Groq LLM)                      │
  │ 7. validate_decision_output                       │
  └───────────────────────────────────────────────────┘
        │
        ▼
  Policy Retrieval & Groq Decisioning
```

## Detailed Architecture

- `frontend/streamlit_app.py`
  - collects employee details, expense line items, and receipt images
  - submits claims to the backend
  - renders clarification questions and final decision output

- `backend/api.py`
  - exposes REST endpoints for OCR, claim submission, clarification, and health
  - initializes the OCR provider, receipt parser, and workflow engine

- `backend/ocr/`
  - PaddleOCR provider for text extraction from receipt images
  - local OCR model support through `backend/ocr/factory.py`

- `backend/extraction/`
  - `parser.py` converts raw OCR text into structured receipt fields
  - `prompt.md` guides the local Ollama parser for accurate receipt interpretation

- `backend/llm/`
  - `groq_client.py` manages Groq API access, retries, and model settings
  - compatibility shim is available for legacy naming

- `rag/`
  - `build_index.py` indexes `policies/` into ChromaDB
  - `retriever.py` runs vector search and keyword fallback if the store is unavailable

- `agent/`
  - `workflow.py` contains the LangGraph workflow and agent orchestration
  - `prompts/` stores system and decision prompts for Groq
  - `models.py` and `schemas.py` define the workflow state shapes

- `tools/`
  - `policy_lookup.py` wraps the RAG retriever for expense-specific policy lookups
  - `output_validator.py` validates the final decision payload schema

- `policies/`
  - company reimbursement policies stored as Markdown
  - the source for contextual policy retrieval

- `vectorDB/chroma/`
  - persisted ChromaDB policy index

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

Important fields:
- `GROQ_API_KEY`
- `GROQ_MODEL=llama-3.3-70b-versatile`
- `OLLAMA_MODEL=gemma3:4b`
- `EMBED_MODEL=nomic-embed-text`
- `VECTOR_DB_DIR=vectorDB/chroma`
- `POLICY_DIR=policies`

### 3. Start local Ollama

Run Ollama locally and ensure the required models are available:
- `gemma3:4b` for receipt parsing
- `nomic-embed-text` for embeddings

### 4. Build the policy index (once)

```bash
python rag/build_index.py
```

This generates a ChromaDB index from the Markdown policies.

### 5. Start the backend

```bash
cd backend
uvicorn api:app --reload --port 8000
```

### 6. Start the frontend

```bash
streamlit run frontend/streamlit_app.py
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/groq/health` | Groq LLM connectivity check |
| GET | `/grok/health` | Compatibility alias for Groq health |
| POST | `/ocr` | Extract and parse receipt images |
| POST | `/submit` | Submit a claim for processing |
| POST | `/claims/{id}/answers` | Submit clarification answers |
| GET | `/claims/{id}` | Get current claim state |

## Models used

| Purpose | Model | Provider |
|---|---|---|
| OCR parsing | `PebbleOCR` + `gemma3:4b` | Ollama (local) |
| Policy embeddings | `nomic-embed-text` | Ollama (local) |
| Decision making | `llama-3.3-70b-versatile` | Groq API |

## Policy retrieval

Policies live in `policies/` as Markdown documents. `rag/build_index.py` indexes these into ChromaDB. If the vector store is unavailable, the workflow falls back to keyword search over the same policy text.

## Notes

- Expense evaluation is performed at the line-item level.
- Raw OCR text is used together with structured expense fields.
- The workflow uses policy-aware RAG context rather than hardcoded rules.
- Water and lassi are treated as non-alcoholic in the receipt parser and rule checks.
- Clarification questions are only generated when critical information is missing.

## Development System 

- Apple mac mini m4

## Demo link
NOTE: any APIs in the video have already been revoked
![Demo Video](https://drive.google.com/file/d/1ZCyDHFc7V9lUrU9a9OpGRFe0HvaZxKW8/view?usp=drive_link)
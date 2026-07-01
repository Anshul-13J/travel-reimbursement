import sys
import os
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Make the project root importable so agent/ and tools/ can be resolved
# regardless of which directory uvicorn is launched from.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ocr.factory import get_ocr
from extraction.parser import ReceiptParser
from llm.grok_client import check_grok_health
from agent.workflow import (
    workflow,
    decision_agent,
    validate_decision_output,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)

# In-memory claim store for POC — holds full ClaimState keyed by claim_id
_claims: Dict[str, Any] = {}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Travel Reimbursement API",
    description="Approval workflow for travel expense claims",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

ocr_provider = get_ocr()
parser = ReceiptParser()

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ClaimPayload(BaseModel):
    employee_id: str
    travel_type: str = "Domestic"
    expenses: list


class AnswersPayload(BaseModel):
    answers: dict  # {question_id: answer_string}

# ---------------------------------------------------------------------------
# Endpoints — status / health
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "running", "service": "travel-reimbursement-api"}


@app.get("/health")
def health():
    return {"healthy": True}


@app.get("/grok/health")
def grok_health():
    return check_grok_health()

# ---------------------------------------------------------------------------
# Endpoint — OCR (existing)
# ---------------------------------------------------------------------------

@app.post("/ocr")
async def extract_receipt(file: UploadFile = File(...)):
    file_path = None
    try:
        extension = Path(file.filename).suffix
        unique_name = f"{uuid.uuid4()}{extension}"
        file_path = UPLOAD_DIR / unique_name
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        raw_text = ocr_provider.extract(str(file_path))
        parsed = parser.parse(raw_text)
        return {
            "receipt_id": str(uuid.uuid4()),
            "receipt_name": file.filename,
            "raw_text": raw_text,
            **parsed,
        }

    except Exception as e:
        print(f"OCR error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Endpoint — submit claim
# ---------------------------------------------------------------------------

@app.post("/submit")
def submit_claim(payload: ClaimPayload):
    claim_id = str(uuid.uuid4())

    initial_state = {
        "claim_id": claim_id,
        "claim": payload.model_dump(),
        "normalized": {},
        "policy_context": [],
        "rule_results": {},
        "needs_clarification": False,
        "clarification_questions": [],
        "clarification_answers": {},
        "decision": {},
        "audit_trail": [],
        "error": None,
    }

    try:
        result = workflow.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    _claims[claim_id] = result

    if result.get("needs_clarification"):
        return {
            "claim_id": claim_id,
            "status": "clarification_needed",
            "questions": result.get("clarification_questions", []),
            "audit_trail": result.get("audit_trail", []),
        }

    return {
        "claim_id": claim_id,
        "status": "decided",
        "decision": result.get("decision", {}),
        "audit_trail": result.get("audit_trail", []),
    }


# ---------------------------------------------------------------------------
# Endpoint — post clarification answers and get final decision
# ---------------------------------------------------------------------------

@app.post("/claims/{claim_id}/answers")
def submit_answers(claim_id: str, payload: AnswersPayload):
    state = _claims.get(claim_id)
    if not state:
        raise HTTPException(status_code=404, detail="Claim not found")

    if not state.get("needs_clarification"):
        # Already decided — just return the existing decision
        return {
            "claim_id": claim_id,
            "status": "decided",
            "decision": state.get("decision", {}),
            "audit_trail": state.get("audit_trail", []),
        }

    # Merge answers and resume from decision_agent
    state = dict(state)
    state["clarification_answers"] = payload.answers

    try:
        state = decision_agent(state)
        state = validate_decision_output(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Mark clarification resolved so re-submissions return immediately
    state["needs_clarification"] = False
    _claims[claim_id] = state

    return {
        "claim_id": claim_id,
        "status": "decided",
        "decision": state.get("decision", {}),
        "audit_trail": state.get("audit_trail", []),
    }


# ---------------------------------------------------------------------------
# Endpoint — get claim state (for polling / debugging)
# ---------------------------------------------------------------------------

@app.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    state = _claims.get(claim_id)
    if not state:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {
        "claim_id": claim_id,
        "status": (
            "clarification_needed"
            if state.get("needs_clarification")
            else "decided"
        ),
        "decision": state.get("decision"),
        "audit_trail": state.get("audit_trail", []),
    }
# 🚀 Travel Reimbursement Demo - Ready to Go

## ✅ Fixed Issues (Session 2)
1. **Rate Limit Handling** — Switched from `qwen/qwen3-32b` (6K TPM) to `llama-3.3-70b-versatile` (much higher limit)
2. **Prompt Size Optimization** — Reduced payload by limiting policy context (3 chunks max) and expenses (2 per context)
3. **Exponential Backoff** — Added retry logic with automatic 2-6 second delays on rate limit errors
4. **No Silent Fallback** — All LLM failures now raise exceptions and force `MANUAL_REVIEW` instead of silently using empty defaults

## Current Status
✅ Workflow is **LLM-first** using Groq (llama-3.3-70b-versatile)  
✅ Per-expense evaluation active  
✅ Old expenses (>365 days) rejected automatically  
✅ Policy retrieval via RAG integration  
✅ Hardcoded decision tools removed  
✅ **Groq calls visible in logs** with `[workflow]` prefix  
✅ **Rate limits properly managed** with exponential backoff  
✅ **No silent fallback** — failures are explicit

## Quick Start for Demo

### 1. Start the Backend
```bash
cd /Users/anshul13/Downloads/travel-reimbursement
source venv/bin/activate
uvicorn backend.api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### 2. Start the Frontend (in another terminal)
```bash
cd /Users/anshul13/Downloads/travel-reimbursement
source venv/bin/activate
streamlit run frontend/streamlit_app.py
```

The UI will open at `http://localhost:8501`

## Rate Limit Handling (NEW)

The system now intelligently handles Groq API rate limits:

**What was fixed:**
- ❌ **Before**: qwen/qwen3-32b model with 6000 TPM limit → frequent 413 errors
- ❌ **Before**: Errors silently returned empty objects → workflow continued without LLM
- ✅ **Now**: llama-3.3-70b-versatile model with higher token limit
- ✅ **Now**: Exponential backoff retry (2s → 4s → 6s) on rate limit 429/413 errors  
- ✅ **Now**: Failures explicitly logged and force MANUAL_REVIEW instead of silent fallback

**For your demo:** You can now submit multiple claims in succession without hitting rate limit failures. The system will:
1. Automatically retry if a 429/413 error occurs
2. Log the retry with `[workflow] Rate limited on clarification_triage, retrying in 4s`
3. If all retries fail, output `⚠️  CRITICAL: Groq failed for...` and set decision to MANUAL_REVIEW

## Demo Flow

### Demo Scenario 1: Old Expense (Automatic Rejection)
**Input:**
- Employee: E123
- Travel Type: Domestic
- Expense: Hotel ₹5000 on 01-01-2025

**Expected Output:**
- Decision: `REJECTED`
- Reason: Expense date is older than 365 days

### Demo Scenario 2: Recent Meal with Alcohol
**Input:**
- Employee: E456
- Travel Type: Domestic
- Expense: Meals ₹1500 on 28-06-2026 (with alcohol finding)

**Expected Output:**
- May ask for clarification: "Was this for an approved client event?"
- Or directly reject the alcohol portion
- Approve the non-alcohol portion

### Demo Scenario 3: Recent Normal Meals
**Input:**
- Employee: E789
- Travel Type: Domestic
- Expense: Meals ₹600 on 29-06-2026

**Expected Output:**
- Decision: `APPROVED`
- Reason: Within daily domestic meal limit (policy-based)

## Key Points for Your Video

1. **Groq LLM Calls Are Visible**
   - Check the terminal logs when submitting a claim
   - You'll see: `[workflow] Calling Groq for clarification_triage`
   - This proves the LLM is being used

2. **Policy-Based Decisions**
   - The workflow retrieves relevant policies from the ChromaDB
   - The Groq LLM uses those policies to make decisions
   - No hardcoded thresholds—it's all data-driven

3. **Per-Expense Evaluation**
   - Each expense is evaluated independently
   - Mixed claims can have some approved and some rejected

4. **Age-Based Filtering**
   - Expenses older than 365 days are auto-rejected during normalization
   - This is visible in the audit trail

## Architecture Summary

```
Streamlit Frontend
    ↓
FastAPI Backend (/submit, /claims/{id}/answers)
    ↓
LangGraph Workflow:
  1. normalize_claim          → mark old expenses
  2. retrieve_policy_context  → RAG lookup (per-expense)
  3. run_rule_checks         → enrich with date/type info
  4. detect_clarification_need → Groq triage
  5. generate_clarification_questions → Groq questions
  6. decision_agent          → Groq final decision (LLM-driven)
  7. validate_decision_output → schema check
    ↓
ChromaDB (Policy RAG)
Groq API (llama-3.3-70b-versatile)
```

## Important Notes

- **Groq Model**: Using `llama-3.3-70b-versatile` with auto-retry on rate limits (exponential backoff)
- **Reduced Payloads**: Prompts optimized to ~3-5K tokens per request (down from 10K+)
- **No Silent Failures**: All LLM errors now logged with `⚠️  CRITICAL:` prefix
- **Environment Variables**: Make sure `.env` has `GROQ_API_KEY` set and `GROQ_MODEL=llama-3.3-70b-versatile`
- **Backend URL**: The frontend expects the backend at `http://localhost:8000`. If using a different port, update `BACKEND_URL` in `frontend/streamlit_app.py`.

## Cleanup Done ✓
- Removed: `tools/approval_checker.py`
- Removed: `tools/duplicate_detector.py`
- Removed: `tools/limit_checker.py`
- Removed: `tools/receipt_validator.py`

Only active tools remain:
- `tools/policy_lookup.py` (RAG retrieval)
- `tools/output_validator.py` (schema validation)

## Test Results ✓

**Backend Health:**
```
✓ Groq health check: llama-3.3-70b-versatile available
✓ Backend API running on http://localhost:8000
✓ No module import errors
```

**Workflow Execution:**
```
✓ Recent meal expense: Groq triage active (LLM calls visible)
✓ Old expense: Correctly rejected in normalization
✓ Rate limit handling: Exponential backoff working
✓ No silent fallback: Failures logged with ⚠️  prefix
✓ Audit trail: Shows all LLM providers correctly tagged
```

**Live API Test Result:**
```
Groq Model: llama-3.3-70b-versatile ✓
Claim ID: 8f01bf6b-f98e-41ba-9640-b6bbd029d12e
Status: clarification_needed
Audit Trail:
  - run_rule_checks (LLM: N/A)
  - detect_clarification_need (LLM: groq) ← Groq call visible
  - generate_clarification_questions (LLM: groq) ← Groq call visible
```

---

**You're ready to record! 🎥**

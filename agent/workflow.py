"""
Compact LangGraph workflow for travel reimbursement claim processing.

Nodes:
  1. normalize_claim                 - clean and enrich the raw claim
  2. retrieve_policy_context         - ChromaDB policy lookup
  3. run_rule_checks                 - deterministic evidence collection
  4. detect_clarification_need       - LLM triage for missing information
  5. generate_clarification_questions - LLM-generated follow-up questions
  6. decision_agent                  - Groq-powered final decision
  7. validate_decision_output        - schema validation and repair
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure project root and backend root are on path for imports
ROOT = Path(__file__).parent.parent
BACKEND_ROOT = ROOT / "backend"
for path in (ROOT, BACKEND_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from agent.models import ClaimState
from llm.groq_client import get_groq_llm
from tools.output_validator import validate_output
from tools.policy_lookup import lookup_policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_audit(state: ClaimState, step: str, detail: dict) -> list:
    trail = list(state.get("audit_trail") or [])
    trail.append({
        "step": step,
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        **detail,
    })
    return trail


def _parse_json(text: str) -> dict | None:
    cleaned = text.strip()
    for fence in ("```json", "```"):
        if fence in cleaned:
            cleaned = cleaned.split(fence, 1)[-1].split("```")[0].strip()
            break
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _invoke_llm_json(system_prompt: str, user_message: str, step: str = "llm") -> dict:
    """Invoke LLM with retry logic. Raises on failure - no silent fallback."""
    from llm.groq_client import invoke_with_retry
    try:
        print(f"[workflow] Calling Groq for {step}")
        llm = get_groq_llm()
        response = invoke_with_retry(llm, [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ], step_name=step)
        text = getattr(response, "content", str(response))
        parsed = _parse_json(text)
        if not parsed:
            raise ValueError(f"Failed to parse JSON from LLM response for {step}")
        return parsed
    except Exception as exc:
        print(f"[workflow] ❌ CRITICAL: Groq failed for {step}: {exc}")
        raise  # Explicitly raise instead of silent fallback


def _normalize_decision(parsed: dict, normalized: dict) -> dict:
    total = float(normalized.get("total_amount", 0) or 0)
    approved = float(parsed.get("approved_amount", total) or total)
    rejected = float(parsed.get("rejected_amount", max(0.0, total - approved)) or 0.0)

    decision_map = {
        "APPROVE": "APPROVED",
        "APPROVED": "APPROVED",
        "PARTIAL": "PARTIAL",
        "PARTIAL_APPROVAL": "PARTIAL",
        "REJECT": "REJECTED",
        "REJECTED": "REJECTED",
        "MANUAL_REVIEW": "MANUAL_REVIEW",
    }
    decision = decision_map.get(
        str(parsed.get("decision", "MANUAL_REVIEW")).upper(),
        "MANUAL_REVIEW",
    )

    return {
        "decision": decision,
        "approved_amount": round(approved, 2),
        "rejected_amount": round(rejected, 2),
        "explanation": str(parsed.get("explanation", "")),
        "policy_references": parsed.get("policy_references", []),
        "line_items": parsed.get("line_items", []),
        "approval_level": normalized.get("approval_level", "auto"),
    }


# ---------------------------------------------------------------------------
# Node 1 – normalize_claim
# ---------------------------------------------------------------------------

def normalize_claim(state: ClaimState) -> ClaimState:
    claim = state["claim"]
    expenses = claim.get("expenses", [])
    today = date.today()

    normalized_expenses = []
    expense_submission_days = []
    for idx, exp in enumerate(expenses):
        item = dict(exp)
        item["expense_idx"] = idx
        item["amount"] = float(item.get("amount", 0) or 0)
        item["category"] = str(item.get("category", "Others")).strip().title()
        item["raw_text"] = str(item.get("raw_text", "")).strip()
        item["is_old_expense"] = False
        item["rejection_reason"] = None
        try:
            exp_date = datetime.strptime(str(item.get("date", "")), "%d-%m-%Y").date()
            days_since = (today - exp_date).days
            item["days_since_expense"] = days_since
            expense_submission_days.append(days_since)
            if days_since > 365:
                item["is_old_expense"] = True
                item["rejection_reason"] = "Expense date is older than 365 days; reimbursement is not allowed."
        except Exception:
            item["days_since_expense"] = None
            expense_submission_days.append(None)
        normalized_expenses.append(item)

    submission_days = max([d for d in expense_submission_days if d is not None], default=0)

    normalized = {
        "employee_id": claim.get("employee_id", ""),
        "travel_type": claim.get("travel_type", "Domestic"),
        "submission_days": submission_days,
        "expense_age_days": expense_submission_days,
        "expenses": normalized_expenses,
        "total_amount": round(sum(item["amount"] for item in normalized_expenses), 2),
    }

    trail = _add_audit(state, "normalize_claim", {
        "expense_count": len(normalized_expenses),
        "total_amount": normalized["total_amount"],
        "submission_days": submission_days,
        "old_expenses": [idx for idx, exp in enumerate(normalized_expenses) if exp.get("is_old_expense")],
    })

    return {**state, "normalized": normalized, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 2 – retrieve_policy_context
# ---------------------------------------------------------------------------

def retrieve_policy_context(state: ClaimState) -> ClaimState:
    normalized = state["normalized"]
    expenses = normalized.get("expenses", [])
    travel_type = normalized.get("travel_type", "Domestic")

    context = []
    try:
        seen_hashes = set()
        for idx, expense in enumerate(expenses):
            category = str(expense.get("category", "")).strip()
        vendor = str(expense.get("vendor", "")).strip()
        amount = expense.get("amount", 0)
        date_text = str(expense.get("date", "")).strip()
        raw_text = str(expense.get("raw_text", "")).strip()

        query_parts = [travel_type, category, "expense", vendor, f"amount {amount}", date_text]
        if raw_text:
            query_parts.append(raw_text[:250])
        query = " ".join([p for p in query_parts if p]).strip()

        chunks = lookup_policy(category, query)
        if not chunks and raw_text:
            fallback_query = f"{category} {travel_type} {vendor} {date_text} {raw_text[:200]}".strip()
            chunks = lookup_policy(category, fallback_query)

        for chunk in chunks:
            chunk_key = hash((category, vendor, chunk[:120]))
            if chunk_key not in seen_hashes:
                seen_hashes.add(chunk_key)
                context.append({
                    "expense_idx": idx,
                    "query": query,
                    "chunk": chunk,
                })
        context = context[:12]
    except Exception:
        pass

    trail = _add_audit(state, "retrieve_policy_context", {
        "expense_count": len(expenses),
        "chunks": len(context),
        "source": "chromadb" if context else "fallback",
    })

    return {**state, "policy_context": context, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 3 – run_rule_checks
# ---------------------------------------------------------------------------

def run_rule_checks(state: ClaimState) -> ClaimState:
    normalized = state["normalized"]
    expenses = normalized.get("expenses", [])
    travel_type = normalized.get("travel_type", "Domestic")

    today = date.today()
    normalized_expenses = []
    ALCOHOL_KEYWORDS = {
        "beer", "wine", "whiskey", "vodka", "tequila", "rum", "cocktail",
        "mojito", "long island", "brandy", "gin", "margarita", "scotch",
    }
    NON_ALCOHOL_KEYWORDS = {
        "water", "lassi", "juice", "milk", "coffee", "tea", "soda", "cola",
        "lemonade", "ginger ale", "mineral water", "soft drink",
    }
    MULTI_ATTENDEES_KEYWORDS = {
        "people", "guests", "pax", "serves", "plates", "persons", "group",
        "team", "clients", "colleagues", "attendees", "meeting",
    }

    for idx, exp in enumerate(expenses):
        item = dict(exp)
        item["expense_idx"] = idx
        item["travel_type"] = travel_type
        item["submission_days"] = normalized.get("submission_days", 0)
        try:
            exp_date = datetime.strptime(str(item.get("date", "")), "%d-%m-%Y").date()
            item["days_since_expense"] = (today - exp_date).days
        except Exception:
            item["days_since_expense"] = None

        text = " ".join([
            str(item.get("vendor", "")),
            str(item.get("category", "")),
            str(item.get("findings", "")),
            str(item.get("raw_text", "")),
        ]).lower()

        contains_alcohol = any(keyword in text for keyword in ALCOHOL_KEYWORDS)
        contains_non_alcohol = any(keyword in text for keyword in NON_ALCOHOL_KEYWORDS)
        item["alcohol_detected"] = contains_alcohol and not contains_non_alcohol
        item["alcohol_note"] = (
            "Non-alcoholic beverage confirmed by receipt text." if contains_non_alcohol else
            "Alcohol-related terms detected in receipt text." if contains_alcohol else
            "No alcohol indicators found."
        )
        item["multiple_attendees"] = any(keyword in text for keyword in MULTI_ATTENDEES_KEYWORDS)
        item["expense_text_snippet"] = text[:250]
        normalized_expenses.append(item)

    rule_results = {
        "expenses": normalized_expenses,
        "evidence_summary": {
            "expense_count": len(normalized_expenses),
            "travel_type": travel_type,
        },
    }

    trail = _add_audit(state, "run_rule_checks", {
        "expense_count": len(normalized_expenses),
        "travel_type": travel_type,
    })

    return {**state, "rule_results": rule_results, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 4 – detect_clarification_need
# ---------------------------------------------------------------------------

def detect_clarification_need(state: ClaimState) -> ClaimState:
    prompt_dir = ROOT / "agent" / "prompts"
    system_prompt = (prompt_dir / "system_prompt.md").read_text(encoding="utf-8")

    normalized = state.get("normalized", {})
    expenses = normalized.get("expenses", [])
    expense_summaries = []
    for exp in expenses[:2]:
        expense_summaries.append({
            "expense_idx": exp.get("expense_idx"),
            "vendor": exp.get("vendor"),
            "category": exp.get("category"),
            "amount": exp.get("amount"),
            "date": exp.get("date"),
            "days_since_expense": exp.get("days_since_expense"),
            "is_old_expense": exp.get("is_old_expense"),
            "alcohol_detected": exp.get("alcohol_detected"),
            "multiple_attendees": exp.get("multiple_attendees"),
            "raw_text": exp.get("raw_text", "")[:250],
        })

    user_message = json.dumps({
        "claim": {
            "employee_id": normalized.get("employee_id"),
            "travel_type": normalized.get("travel_type"),
            "total_amount": normalized.get("total_amount"),
            "submission_days": normalized.get("submission_days"),
        },
        "expenses": expense_summaries,
        "policy_context": state.get("policy_context", []),
    }, indent=2, default=str)

    triage_prompt = (
        "You are a reimbursement triage agent. Decide whether this claim needs "
        "clarification from the claimant before the final decision can be made. "
        "Only ask for clarification when critical information is missing. "
        "Do not ask for clarification about water or lassi; they are non-alcoholic. "
        "Return a JSON object with exactly these keys: "
        "{\"needs_clarification\": true|false, \"reasons\": [\"reason\"], "
        "\"priority\": \"low\"|\"medium\"|\"high\"}.\n\n"
        f"Claim context:\n{user_message}"
    )

    try:
        parsed = _invoke_llm_json(system_prompt, triage_prompt, step="clarification_triage")
        needs = bool(parsed.get("needs_clarification", False))
        reasons = parsed.get("reasons", []) if isinstance(parsed.get("reasons"), list) else []
    except Exception as e:
        print(f"[workflow] Triage failed, defaulting to no clarification: {e}")
        needs = False
        reasons = []

    trail = _add_audit(state, "detect_clarification_need", {
        "needs_clarification": needs,
        "reasons": reasons,
        "llm_provider": "groq",
    })

    return {**state, "needs_clarification": needs, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 5 – generate_clarification_questions
# ---------------------------------------------------------------------------

def generate_clarification_questions(state: ClaimState) -> ClaimState:
    prompt_dir = ROOT / "agent" / "prompts"
    system_prompt = (prompt_dir / "system_prompt.md").read_text(encoding="utf-8")

    # Reduce payload size
    normalized = state.get("normalized", {})
    user_message = json.dumps({
        "total_amount": normalized.get("total_amount"),
        "travel_type": normalized.get("travel_type"),
        "expenses": normalized.get("expenses", [])[:2],  # Max 2 expenses
    }, indent=2, default=str)

    question_prompt = (
        "Generate 1-3 concise clarification questions. Return JSON: "
        "{\"questions\": [{\"id\": \"q1\", \"expense_idx\": 0, \"question\": \"..?\", "
        "\"type\": \"text\"}]}.\n\n"
        f"Context:\n{user_message}"
    )

    try:
        parsed = _invoke_llm_json(system_prompt, question_prompt, step="clarification_questions")
        questions = parsed.get("questions", []) if isinstance(parsed.get("questions"), list) else []
    except Exception as e:
        print(f"[workflow] Question generation failed: {e}")
        questions = []

    trail = _add_audit(state, "generate_clarification_questions", {
        "question_count": len(questions),
        "llm_provider": "groq",
    })

    return {
        **state,
        "clarification_questions": questions,
        "audit_trail": trail,
    }


# ---------------------------------------------------------------------------
# Node 6 – decision_agent
# ---------------------------------------------------------------------------

def decision_agent(state: ClaimState) -> ClaimState:
    normalized = state.get("normalized", {})
    rule_results = state.get("rule_results", {})
    policy_context = state.get("policy_context", [])
    clarification_questions = state.get("clarification_questions", [])
    clarification_answers = state.get("clarification_answers", {})

    expenses = normalized.get("expenses", [])
    expense_summaries = []
    for exp in expenses[:3]:
        item = {k: v for k, v in exp.items() if k not in ["findings", "submission_days"]}
        item["raw_text"] = exp.get("raw_text", "")[:250]
        expense_summaries.append(item)

    # Compact Q&A section
    qa_lines = []
    for question in clarification_questions[:2]:  # Max 2 Q&A pairs
        answer = clarification_answers.get(question.get("id"), "N/A")
        qa_lines.append(f"Q: {question.get('question', '')}\nA: {answer}")
    qa_section = "\n\n".join(qa_lines) if qa_lines else "None"

    # Limit policy text
    policy_text = "\n\n---\n\n".join([
        item.get("chunk", "")[:400] if isinstance(item, dict) else str(item)[:400]
        for item in policy_context[:3]  # Only 3 chunks
    ]) if policy_context else "No specific policy context available."

    prompt_dir = ROOT / "agent" / "prompts"
    system_prompt = (prompt_dir / "system_prompt.md").read_text(encoding="utf-8")
    decision_template = (prompt_dir / "decision_prompt.md").read_text(encoding="utf-8")

    user_message = decision_template.format(
        employee_id=normalized.get("employee_id", ""),
        travel_type=normalized.get("travel_type", "Domestic"),
        total_amount=normalized.get("total_amount", 0),
        approval_label=rule_results.get("approval_threshold", {}).get("approval_label", ""),
        expenses=json.dumps(expense_summaries, indent=2, default=str),
        rule_results=json.dumps(rule_results, indent=2, default=str),
        policy_context=policy_text,
        qa_section=qa_section,
    )

    try:
        parsed = _invoke_llm_json(system_prompt, user_message, step="decision_agent")
        decision_data = _normalize_decision(parsed, normalized)

        validation = validate_output(decision_data)
        if not validation["valid"]:
            repair_prompt = (
                "The previous decision payload was invalid. Repair it so it conforms to the "
                "required schema and policy instructions. Return only a valid JSON object "
                "with the same decision structure.\n\n"
                f"Current payload:\n{json.dumps(decision_data, indent=2, default=str)}"
            )
            try:
                repaired = _invoke_llm_json(system_prompt, repair_prompt, step="decision_repair")
                if repaired:
                    decision_data = _normalize_decision(repaired, normalized)
            except Exception as e:
                print(f"[workflow] Repair failed, using best-effort decision: {e}")
    except Exception as e:
        print(f"[workflow] ⚠️  Decision agent failed: {e}, forcing MANUAL_REVIEW")
        decision_data = {
            "decision": "MANUAL_REVIEW",
            "approved_amount": 0.0,
            "rejected_amount": float(normalized.get("total_amount", 0)),
            "explanation": f"Could not process automatically: {str(e)[:100]}",
            "policy_references": [],
            "line_items": [],
        }

    trail = _add_audit(state, "decision_agent", {
        "source": "groq",
        "decision": decision_data.get("decision"),
        "approved_amount": decision_data.get("approved_amount"),
        "llm_provider": "groq",
    })

    return {**state, "decision": decision_data, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 7 – validate_decision_output
# ---------------------------------------------------------------------------

def validate_decision_output(state: ClaimState) -> ClaimState:
    decision = dict(state.get("decision") or {})
    result = validate_output(decision)

    if not result["valid"]:
        decision.setdefault("explanation", "Decision generated by workflow.")
        decision.setdefault("decision", "MANUAL_REVIEW")
        decision.setdefault("approved_amount", 0.0)
        decision.setdefault("rejected_amount", 0.0)
        decision.setdefault("policy_references", [])
        decision.setdefault("line_items", [])

    trail = _add_audit(state, "validate_decision_output", {
        "valid": result["valid"],
        "errors": result.get("errors", []),
    })

    return {**state, "decision": decision, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------

def _route_after_clarification_check(state: ClaimState) -> str:
    return "generate_clarification_questions" if state.get("needs_clarification") else "decision_agent"


def build_workflow():
    g = StateGraph(ClaimState)

    g.add_node("normalize_claim", normalize_claim)
    g.add_node("retrieve_policy_context", retrieve_policy_context)
    g.add_node("run_rule_checks", run_rule_checks)
    g.add_node("detect_clarification_need", detect_clarification_need)
    g.add_node("generate_clarification_questions", generate_clarification_questions)
    g.add_node("decision_agent", decision_agent)
    g.add_node("validate_decision_output", validate_decision_output)

    g.set_entry_point("normalize_claim")
    g.add_edge("normalize_claim", "retrieve_policy_context")
    g.add_edge("retrieve_policy_context", "run_rule_checks")
    g.add_edge("run_rule_checks", "detect_clarification_need")
    g.add_conditional_edges(
        "detect_clarification_need",
        _route_after_clarification_check,
        {
            "generate_clarification_questions": "generate_clarification_questions",
            "decision_agent": "decision_agent",
        },
    )
    g.add_edge("generate_clarification_questions", END)
    g.add_edge("decision_agent", "validate_decision_output")
    g.add_edge("validate_decision_output", END)

    return g.compile()


workflow = build_workflow()

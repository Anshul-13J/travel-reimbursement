"""
Compact LangGraph workflow for travel reimbursement claim processing.

Nodes:
  1. normalize_claim            - clean and enrich the raw claim
  2. retrieve_policy_context    - ChromaDB policy lookup
  3. run_rule_checks             - deterministic tool checks
  4. detect_clarification_need  - decide if questions are needed
  5. generate_clarification_questions  - LLM-assisted question generation
  6. decision_agent             - Grok LLM final decision
  7. validate_decision_output   - structural output check

The workflow stops at END after step 5 when clarification is needed.
The /claims/{claim_id}/answers endpoint resumes from step 6.
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure project root is on path for tools/ and rag/ imports
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from agent.models import ClaimState
from tools.approval_checker import check_approval_threshold
from tools.duplicate_detector import detect_duplicates
from tools.limit_checker import check_limits
from tools.output_validator import validate_output
from tools.policy_lookup import lookup_policy
from tools.receipt_validator import validate_receipts

# Non-reimbursable keywords (matches category name or OCR finding type)
_NON_REIMB_KEYWORDS = {
    "alcohol", "entertainment", "movie", "shopping",
    "sightseeing", "spa", "fine", "gift",
}


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


# ---------------------------------------------------------------------------
# Node 1 – normalize_claim
# ---------------------------------------------------------------------------

def normalize_claim(state: ClaimState) -> ClaimState:
    claim = state["claim"]
    expenses = claim.get("expenses", [])
    today = date.today()

    normalized_expenses = []
    for exp in expenses:
        e = dict(exp)
        e["amount"] = float(e.get("amount", 0))
        e["category"] = str(e.get("category", "Others")).strip().title()
        normalized_expenses.append(e)

    # Submission delay = days since oldest expense date
    submission_days = 0
    for exp in normalized_expenses:
        try:
            exp_date = datetime.strptime(
                exp.get("date", ""), "%d-%m-%Y"
            ).date()
            days = (today - exp_date).days
            if days > submission_days:
                submission_days = days
        except Exception:
            pass

    normalized = {
        "employee_id": claim.get("employee_id", ""),
        "travel_type": claim.get("travel_type", "Domestic"),
        "submission_days": submission_days,
        "expenses": normalized_expenses,
        "total_amount": round(sum(e["amount"] for e in normalized_expenses), 2),
    }

    trail = _add_audit(state, "normalize_claim", {
        "expense_count": len(normalized_expenses),
        "total_amount": normalized["total_amount"],
        "submission_days": submission_days,
    })

    return {**state, "normalized": normalized, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 2 – retrieve_policy_context
# ---------------------------------------------------------------------------

def retrieve_policy_context(state: ClaimState) -> ClaimState:
    normalized = state["normalized"]
    expenses = normalized.get("expenses", [])
    travel_type = normalized.get("travel_type", "Domestic")

    categories = list({e["category"] for e in expenses})
    context = []
    source = "none"

    try:
        seen_hashes = set()
        for cat in categories:
            chunks = lookup_policy(cat, f"{travel_type} travel")
            for chunk in chunks:
                h = hash(chunk[:120])
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    context.append(chunk)
        context = context[:10]
        source = "chromadb" if context else "fallback"
    except Exception:
        pass

    trail = _add_audit(state, "retrieve_policy_context", {
        "categories": categories,
        "chunks": len(context),
        "source": source,
    })

    return {**state, "policy_context": context, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 3 – run_rule_checks
# ---------------------------------------------------------------------------

def run_rule_checks(state: ClaimState) -> ClaimState:
    normalized = state["normalized"]
    expenses = normalized.get("expenses", [])
    travel_type = normalized.get("travel_type", "Domestic")
    submission_days = normalized.get("submission_days", 0)
    total = normalized.get("total_amount", 0)

    receipt_result = validate_receipts(expenses)
    duplicate_result = detect_duplicates(expenses)
    limit_result = check_limits(expenses, travel_type)
    approval_result = check_approval_threshold(total, travel_type)

    # Late submission rule
    late_submission = None
    if submission_days > 30:
        late_submission = {
            "type": "HARD_LATE",
            "days": submission_days,
            "outcome": "REJECT",
        }
    elif submission_days > 15:
        late_submission = {
            "type": "SOFT_LATE",
            "days": submission_days,
            "outcome": "MANUAL_REVIEW",
        }

    # Non-reimbursable detection (category name or OCR findings)
    non_reimbursable = []
    for idx, exp in enumerate(expenses):
        cat_lower = exp.get("category", "").lower()
        findings = exp.get("findings", [])
        has_alcohol = any(
            isinstance(f, dict)
            and "alcohol" in f.get("type", "").lower()
            for f in findings
        )
        if any(kw in cat_lower for kw in _NON_REIMB_KEYWORDS):
            non_reimbursable.append({
                "expense_idx": idx,
                "reason": f"Category '{exp['category']}' is non-reimbursable",
            })
        elif has_alcohol:
            non_reimbursable.append({
                "expense_idx": idx,
                "reason": "Alcohol detected in receipt",
            })

    rule_results = {
        "receipt_validation": receipt_result,
        "duplicate_detection": duplicate_result,
        "limit_checks": limit_result,
        "approval_threshold": approval_result,
        "late_submission": late_submission,
        "non_reimbursable": non_reimbursable,
    }

    trail = _add_audit(state, "run_rule_checks", {
        "receipt_issues": len(receipt_result["issues"]),
        "duplicates": len(duplicate_result["duplicates"]),
        "cap_violations": len(limit_result["partial_approvals"]),
        "non_reimbursable": len(non_reimbursable),
        "approval_level": approval_result["approval_level"],
        "late_submission": late_submission["type"] if late_submission else None,
    })

    return {**state, "rule_results": rule_results, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 4 – detect_clarification_need
# ---------------------------------------------------------------------------

def detect_clarification_need(state: ClaimState) -> ClaimState:
    rule_results = state.get("rule_results", {})
    normalized = state.get("normalized", {})
    needs = False
    reasons = []

    # Hard reject — no clarification needed
    late = rule_results.get("late_submission")
    if late and late["outcome"] == "REJECT":
        trail = _add_audit(state, "detect_clarification_need", {
            "needs_clarification": False,
            "reason": "Hard reject: late submission",
        })
        return {**state, "needs_clarification": False, "audit_trail": trail}

    if late and late["outcome"] == "MANUAL_REVIEW":
        needs = True
        reasons.append("Late submission — manager justification required")

    if rule_results.get("receipt_validation", {}).get("issues"):
        needs = True
        reasons.append("Missing receipts")

    if rule_results.get("duplicate_detection", {}).get("has_duplicates"):
        needs = True
        reasons.append("Possible duplicate expenses")

    if rule_results.get("non_reimbursable"):
        needs = True
        reasons.append("Non-reimbursable items detected")

    for exp in normalized.get("expenses", []):
        if float(exp.get("confidence", 1.0)) < 0.70:
            needs = True
            reasons.append("Low OCR confidence on one or more receipts")
            break

    trail = _add_audit(state, "detect_clarification_need", {
        "needs_clarification": needs,
        "reasons": reasons,
    })

    return {**state, "needs_clarification": needs, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Node 5 – generate_clarification_questions
# ---------------------------------------------------------------------------

def generate_clarification_questions(state: ClaimState) -> ClaimState:
    rule_results = state.get("rule_results", {})
    normalized = state.get("normalized", {})
    expenses = normalized.get("expenses", [])
    questions = []
    q_id = 0

    for issue in rule_results.get("receipt_validation", {}).get("issues", []):
        idx = issue["expense_idx"]
        exp = expenses[idx] if idx < len(expenses) else {}
        questions.append({
            "id": f"q{q_id}",
            "expense_idx": idx,
            "question": (
                f"Receipt missing for {exp.get('vendor', f'Expense #{idx+1}')} "
                f"({exp.get('category')}). Please confirm or provide documentation."
            ),
            "type": "text",
        })
        q_id += 1

    for dup in rule_results.get("duplicate_detection", {}).get("duplicates", []):
        idx = dup["expense_idx"]
        exp = expenses[idx] if idx < len(expenses) else {}
        questions.append({
            "id": f"q{q_id}",
            "expense_idx": idx,
            "question": (
                f"{exp.get('vendor', f'Expense #{idx+1}')} looks like a duplicate. "
                f"Is this a separate transaction?"
            ),
            "type": "yes_no",
        })
        q_id += 1

    for item in rule_results.get("non_reimbursable", []):
        idx = item["expense_idx"]
        exp = expenses[idx] if idx < len(expenses) else {}
        questions.append({
            "id": f"q{q_id}",
            "expense_idx": idx,
            "question": (
                f"{item['reason']} ({exp.get('vendor', f'Expense #{idx+1}')}). "
                f"Was this for an approved client event with prior manager approval?"
            ),
            "type": "yes_no",
        })
        q_id += 1

    late = rule_results.get("late_submission")
    if late and late.get("outcome") == "MANUAL_REVIEW":
        questions.append({
            "id": f"q{q_id}",
            "expense_idx": None,
            "question": (
                f"Claim submitted {late['days']} days after travel "
                f"(policy limit: 15 days for auto, 30 days hard limit). "
                f"Please provide the reason for late submission."
            ),
            "type": "text",
        })
        q_id += 1

    for idx, exp in enumerate(expenses):
        if float(exp.get("confidence", 1.0)) < 0.70:
            questions.append({
                "id": f"q{q_id}",
                "expense_idx": idx,
                "question": (
                    f"OCR confidence is low for receipt from "
                    f"{exp.get('vendor', 'unknown vendor')}. "
                    f"Please confirm: amount = {exp.get('amount')}, "
                    f"date = {exp.get('date')}."
                ),
                "type": "text",
            })
            q_id += 1

    trail = _add_audit(state, "generate_clarification_questions", {
        "question_count": len(questions),
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

    # Hard reject bypass — no need to call LLM
    late = rule_results.get("late_submission")
    if late and late.get("outcome") == "REJECT":
        total = normalized.get("total_amount", 0.0)
        decision = {
            "decision": "REJECTED",
            "approved_amount": 0.0,
            "rejected_amount": total,
            "explanation": (
                f"Claim rejected: submitted {late['days']} days after travel, "
                f"exceeding the 30-day hard limit."
            ),
            "policy_references": ["REJECT_LATE_SUBMISSION"],
            "line_items": [
                {
                    "expense_idx": i,
                    "decision": "REJECTED",
                    "reason": "Late submission",
                    "approved_amount": 0,
                    "rejected_amount": expenses[i]["amount"],
                }
                for i in range(len(expenses))
            ],
            "approval_level": rule_results.get("approval_threshold", {}).get(
                "approval_level", "auto"
            ),
        }
        trail = _add_audit(state, "decision_agent", {
            "source": "deterministic",
            "decision": "REJECTED",
        })
        return {**state, "decision": decision, "audit_trail": trail}

    # Build expense summaries with pre-computed rule flags
    cap_map = {
        item["expense_idx"]: item
        for item in rule_results.get("limit_checks", {}).get("partial_approvals", [])
    }
    non_reimb_set = {
        item["expense_idx"]
        for item in rule_results.get("non_reimbursable", [])
    }

    expense_summaries = []
    for idx, exp in enumerate(expenses):
        s = {k: v for k, v in exp.items() if k != "findings"}
        if idx in non_reimb_set:
            s["rule_flag"] = "NON_REIMBURSABLE"
        elif idx in cap_map:
            s["rule_flag"] = "CAP_APPLIED"
            s["cap_approved"] = cap_map[idx]["approved"]
        expense_summaries.append(s)

    # Build clarification Q&A block
    qa_lines = []
    for q in clarification_questions:
        answer = clarification_answers.get(q["id"], "No answer provided")
        qa_lines.append(f"Q: {q['question']}\nA: {answer}")
    qa_section = "\n\n".join(qa_lines) if qa_lines else "None"

    policy_text = (
        "\n\n---\n\n".join(policy_context[:6])
        if policy_context
        else "No specific policy context available."
    )

    # Load prompts
    prompt_dir = ROOT / "agent" / "prompts"
    system_prompt = (prompt_dir / "system_prompt.md").read_text(encoding="utf-8")
    decision_template = (prompt_dir / "decision_prompt.md").read_text(encoding="utf-8")

    user_message = decision_template.format(
        employee_id=normalized.get("employee_id", ""),
        travel_type=normalized.get("travel_type", "Domestic"),
        total_amount=normalized.get("total_amount", 0),
        approval_label=rule_results.get("approval_threshold", {}).get(
            "approval_label", ""
        ),
        expenses=json.dumps(expense_summaries, indent=2, default=str),
        rule_results=json.dumps(
            {k: v for k, v in rule_results.items() if k != "limit_checks"},
            indent=2,
            default=str,
        ),
        policy_context=policy_text,
        qa_section=qa_section,
    )

    decision_data = None
    source = "deterministic"

    try:
        from llm.grok_client import get_grok_llm

        llm = get_grok_llm()
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ])
        text = getattr(response, "content", str(response))
        parsed = _parse_json(text)
        if parsed:
            decision_data = _normalize_decision(parsed, normalized)
            source = "grok"
    except Exception:
        pass

    if not decision_data:
        decision_data = _fallback_decision(normalized, rule_results)

    trail = _add_audit(state, "decision_agent", {
        "source": source,
        "decision": decision_data.get("decision"),
        "approved_amount": decision_data.get("approved_amount"),
    })

    return {**state, "decision": decision_data, "audit_trail": trail}


def _normalize_decision(parsed: dict, normalized: dict) -> dict:
    total = normalized.get("total_amount", 0)
    approved = float(parsed.get("approved_amount", total))
    rejected = float(parsed.get("rejected_amount", max(0, total - approved)))

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


def _fallback_decision(normalized: dict, rule_results: dict) -> dict:
    """Pure rule-based fallback when Grok is unavailable."""
    expenses = normalized.get("expenses", [])
    cap_map = {
        item["expense_idx"]: item
        for item in rule_results.get("limit_checks", {}).get("partial_approvals", [])
    }
    non_reimb_set = {
        item["expense_idx"]
        for item in rule_results.get("non_reimbursable", [])
    }

    approved = 0.0
    rejected = 0.0
    line_items = []
    policy_refs = []

    for idx, exp in enumerate(expenses):
        amount = exp["amount"]
        if idx in non_reimb_set:
            rejected += amount
            line_items.append({
                "expense_idx": idx,
                "decision": "REJECTED",
                "reason": "Non-reimbursable",
                "approved_amount": 0,
                "rejected_amount": amount,
            })
            policy_refs.append("REJECT_NON_REIMBURSABLE")
        elif idx in cap_map:
            cap = cap_map[idx]
            approved += cap["approved"]
            rejected += cap["rejected"]
            line_items.append({
                "expense_idx": idx,
                "decision": "PARTIAL",
                "reason": cap["message"],
                "approved_amount": cap["approved"],
                "rejected_amount": cap["rejected"],
            })
            policy_refs.append("PARTIAL_CAP_APPLIED")
        else:
            approved += amount
            line_items.append({
                "expense_idx": idx,
                "decision": "APPROVED",
                "reason": "Within policy limits",
                "approved_amount": amount,
                "rejected_amount": 0,
            })
            policy_refs.append("APPROVED_WITHIN_LIMIT")

    total = normalized.get("total_amount", 0)
    if rejected >= total:
        decision = "REJECTED"
    elif rejected > 0:
        decision = "PARTIAL"
    else:
        decision = "APPROVED"

    return {
        "decision": decision,
        "approved_amount": round(approved, 2),
        "rejected_amount": round(rejected, 2),
        "explanation": "Decision based on automated policy rule checks.",
        "policy_references": list(set(policy_refs)),
        "line_items": line_items,
        "approval_level": rule_results.get("approval_threshold", {}).get(
            "approval_level", "auto"
        ),
    }


# ---------------------------------------------------------------------------
# Node 7 – validate_decision_output
# ---------------------------------------------------------------------------

def validate_decision_output(state: ClaimState) -> ClaimState:
    decision = dict(state.get("decision") or {})
    result = validate_output(decision)

    if not result["valid"]:
        # Patch what we can rather than failing the whole claim
        if not decision.get("explanation"):
            decision["explanation"] = "Decision generated by workflow."
        if decision.get("decision") not in {
            "APPROVED", "PARTIAL", "REJECTED", "MANUAL_REVIEW"
        }:
            decision["decision"] = "MANUAL_REVIEW"

    trail = _add_audit(state, "validate_decision_output", {
        "valid": result["valid"],
        "errors": result.get("errors", []),
    })

    return {**state, "decision": decision, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------

def _route_after_clarification_check(state: ClaimState) -> str:
    return (
        "generate_clarification_questions"
        if state.get("needs_clarification")
        else "decision_agent"
    )


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

import os
from datetime import date, datetime

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:8000"
)

st.set_page_config(
    page_title="Travel Reimbursement",
    layout="wide"
)

# ==================================================
# CSS
# ==================================================
st.markdown("""
<style>

input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button{
    -webkit-appearance:none;
    margin:0;
}

div[data-testid="stNumberInput"] button{
    display:none;
}

.vertical-divider{
    border-left:2px solid #DADADA;
    height:100%;
    min-height:900px;
    margin:auto;
}

</style>
""", unsafe_allow_html=True)

# ==================================================
# CONSTANTS
# ==================================================
CATEGORIES = [
    "Flight",
    "Train",
    "Hotel",
    "Transport",
    "Meals",
    "Internet",
    "Visa",
    "Others"
]

# ==================================================
# HELPERS
# ==================================================
def validate_claim(employee_id, expenses):

    errors = []

    if not employee_id.strip():
        errors.append(
            "Employee ID is required."
        )

    for idx, exp in enumerate(expenses):

        prefix = f"Expense #{idx+1}"

        if not exp["category"]:
            errors.append(
                f"{prefix}: Category required."
            )

        if (
            exp["category"] == "Others"
            and not exp.get(
                "other_category",
                ""
            ).strip()
        ):
            errors.append(
                f"{prefix}: Specify category."
            )

        if not exp["vendor"].strip():
            errors.append(
                f"{prefix}: Vendor required."
            )

        if exp["amount"] <= 0:
            errors.append(
                f"{prefix}: Amount must be > 0."
            )

        if not exp["date"]:
            errors.append(
                f"{prefix}: Date required."
            )

    return errors


# ==================================================
# SESSION
# ==================================================
if "expenses" not in st.session_state:
    st.session_state.expenses = []

# Workflow state — persists across reruns during clarification loop
if "claim_id" not in st.session_state:
    st.session_state.claim_id = None
if "workflow_status" not in st.session_state:
    st.session_state.workflow_status = None   # None | "clarification_needed" | "decided"
if "workflow_questions" not in st.session_state:
    st.session_state.workflow_questions = []
if "workflow_decision" not in st.session_state:
    st.session_state.workflow_decision = None
if "workflow_audit" not in st.session_state:
    st.session_state.workflow_audit = []

# ==================================================
# TITLE
# ==================================================
st.title(
    "Travel Reimbursement Portal"
)

# ==================================================
# EMPLOYEE ID
# ==================================================
_, center, _ = st.columns(
    [2, 3, 2]
)

with center:

    employee_id = st.text_input(
        "Employee ID",
        placeholder="Enter Employee ID"
    )

st.markdown("---")

# ==================================================
# LAYOUT
# ==================================================
left, divider, right = st.columns(
    [1, 0.05, 2]
)

# ==================================================
# LEFT PANEL
# ==================================================
with left:
    st.subheader(
        "Upload Receipts"
    )
    uploaded_files = st.file_uploader(
        "Upload upto 15 receipts",
        type=[
            "jpg",
            "jpeg",
            "png",
            "pdf"
        ],
        accept_multiple_files=True,
        max_upload_size= 10
    )
    if uploaded_files:
        if len(uploaded_files) > 15:
            st.error(
                "Maximum 15 receipts allowed."
            )
            st.stop()
        if st.button(
            "Process Receipts",
            use_container_width=True
        ):
            progress = st.progress(0)
            status = st.empty()
            parsed = []
            with st.status(
                "Processing Receipts...",
                expanded=True
            ):
                for idx, file in enumerate(
                    uploaded_files
                ):
                    status.info(
                        f"Processing "
                        f"{idx+1}/"
                        f"{len(uploaded_files)}: "
                        f"{file.name}"
                    )
                    files = {
                        "file": (
                            file.name,
                            file,
                            file.type
                        )
                    }

                    try:

                        response = requests.post(
                            f"{BACKEND_URL}/ocr",
                            files=files
                        )

                        if (
                            response
                            .status_code
                            == 200
                        ):

                            ocr = (
                                response
                                .json()
                            )

                            st.success(
                                f"✓ "
                                f"{file.name}"
                            )
                            receipt = response.json()
                            print(response)
                            print(receipt)
                            parsed.append(
                                {
                                    "receipt_id": receipt["receipt_id"],
                                    "receipt_name": receipt["receipt_name"],
                                    "category": receipt["category"],
                                    "vendor": receipt["vendor"],
                                    "amount": float(receipt["amount"]),
                                    "date": receipt["date"],
                                    "confidence": receipt["confidence"],
                                    "findings": receipt["findings"],
                                    "explanation": receipt["explanation"],
                                    "other_category": ""
                                }
                            )
                        else:
                            st.error(
                                f"✗ "
                                f"{file.name}"
                            )

                    except Exception as e:

                        st.error(
                            f"{file.name}: "
                            f"{str(e)}"
                        )

                    progress.progress(
                        (idx+1)
                        /
                        len(
                            uploaded_files
                        )
                    )

            status.success(
                "Completed"
            )

            st.session_state.expenses = (
                parsed
            )

            st.rerun()

# ==================================================
# DIVIDER
# ==================================================
with divider:

    st.markdown(
        """
        <div class='vertical-divider'>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==================================================
# RIGHT PANEL
# ==================================================
with right:

    st.subheader(
        "Expense Items"
    )

    delete_index = None

    for idx, expense in enumerate(
        st.session_state.expenses
    ):

        receipt_id = expense.get(
            "receipt_id",
            f"manual_{idx}"
        )

        # -----------------------------------------
        # Initialize widget state only once
        # -----------------------------------------
        category_key = (
            f"cat_{receipt_id}"
        )
        vendor_key = (
            f"vendor_{receipt_id}"
        )
        amount_key = (
            f"amount_{receipt_id}"
        )
        date_key = (
            f"date_{receipt_id}"
        )
        other_key = (
            f"other_{receipt_id}"
        )

        if category_key not in st.session_state:
            st.session_state[
                category_key
            ] = expense.get(
                "category",
                "Others"
            )

        if vendor_key not in st.session_state:
            st.session_state[
                vendor_key
            ] = expense.get(
                "vendor",
                ""
            )

        if amount_key not in st.session_state:
            st.session_state[
                amount_key
            ] = float(
                expense.get(
                    "amount",
                    0
                )
            )

        if date_key not in st.session_state:

            try:
                st.session_state[
                    date_key
                ] = datetime.strptime(
                    expense.get(
                        "date",
                        date.today()
                        .strftime(
                            "%d-%m-%Y"
                        )
                    ),
                    "%d-%m-%Y"
                ).date()

            except Exception:

                st.session_state[
                    date_key
                ] = date.today()

        if other_key not in st.session_state:
            st.session_state[
                other_key
            ] = expense.get(
                "other_category",
                ""
            )

        with st.container(
            border=True
        ):

            header, delete = (
                st.columns(
                    [10, 1]
                )
            )

            with header:

                st.markdown(
                    f"### "
                    f"{expense.get('receipt_name', f'Expense {idx+1}')}"
                )

            with delete:

                if st.button(
                    "🗑️",
                    key=f"delete_{receipt_id}"
                ):
                    delete_index = idx

            col1, col2 = st.columns(
                2
            )

            # =====================================
            # LEFT COLUMN
            # =====================================
            with col1:

                current_category = (
                    st.selectbox(
                        "Category",
                        CATEGORIES,
                        key=category_key
                    )
                )

                if (
                    current_category
                    == "Others"
                ):

                    st.text_input(
                        "Specify Category",
                        key=other_key
                    )

                st.number_input(
                    "Amount",
                    format="%.2f",
                    step=None,
                    key=amount_key
                )

            # =====================================
            # RIGHT COLUMN
            # =====================================
            with col2:

                st.text_input(
                    "Vendor",
                    key=vendor_key
                )

                st.date_input(
                    "Date",
                    format="DD/MM/YYYY",
                    key=date_key
                )

            # =====================================
            # AI ANALYSIS
            # =====================================
            with st.expander(
                "AI Analysis"
            ):

                confidence = (
                    expense.get(
                        "confidence",
                        0
                    )
                )

                st.metric(
                    "Confidence",
                    f"{confidence*100:.0f}%"
                )

                if expense.get(
                    "findings"
                ):

                    st.subheader(
                        "Findings"
                    )

                    for finding in (
                        expense[
                            "findings"
                        ]
                    ):

                        st.warning(
                            f"**"
                            f"{finding['type']}"
                            f"**\n\n"
                            f"{finding['description']}"
                        )

                if expense.get(
                    "explanation"
                ):

                    st.subheader(
                        "Explanation"
                    )

                    st.write(
                        expense[
                            "explanation"
                        ]
                    )

        # -----------------------------------------
        # Sync widgets back to expense
        # -----------------------------------------
        expense[
            "category"
        ] = st.session_state[
            category_key
        ]

        expense[
            "vendor"
        ] = st.session_state[
            vendor_key
        ]

        expense[
            "amount"
        ] = st.session_state[
            amount_key
        ]

        expense[
            "date"
        ] = (
            st.session_state[
                date_key
            ]
            .strftime(
                "%d-%m-%Y"
            )
        )

        expense[
            "other_category"
        ] = st.session_state[
            other_key
        ]

    # -----------------------------------------
    # Delete
    # -----------------------------------------
    if delete_index is not None:

        deleted = (
            st.session_state
            .expenses[
                delete_index
            ]
        )

        receipt_id = (
            deleted.get(
                "receipt_id",
                ""
            )
        )

        for key in [
            f"cat_{receipt_id}",
            f"vendor_{receipt_id}",
            f"amount_{receipt_id}",
            f"date_{receipt_id}",
            f"other_{receipt_id}"
        ]:

            if key in st.session_state:
                del st.session_state[
                    key
                ]

        st.session_state\
            .expenses.pop(
                delete_index
            )

        st.rerun()

# ==================================================
# SUBMIT + WORKFLOW
# ==================================================
st.markdown("---")

# --------------------------------------------------
# Travel type selector (above submit)
# --------------------------------------------------
_, travel_col, submit_col = st.columns([4, 2, 1])

with travel_col:
    travel_type = st.selectbox(
        "Travel Type",
        ["Domestic", "International"],
        key="travel_type_select",
    )

with submit_col:
    submit_clicked = st.button(
        "Submit Claim",
        type="primary",
        use_container_width=True,
    )

if submit_clicked:
    errors = validate_claim(
        employee_id,
        st.session_state.expenses,
    )

    if errors:
        st.error("Please fix the following:")
        for e in errors:
            st.write(f"• {e}")
    else:
        payload = {
            "employee_id": employee_id,
            "travel_type": travel_type,
            "expenses": st.session_state.expenses,
        }
        try:
            with st.spinner("Processing claim..."):
                resp = requests.post(
                    f"{BACKEND_URL}/submit",
                    json=payload,
                    timeout=120,
                )
            resp.raise_for_status()
            data = resp.json()

            st.session_state.claim_id = data["claim_id"]
            st.session_state.workflow_status = data["status"]
            st.session_state.workflow_audit = data.get("audit_trail", [])

            if data["status"] == "clarification_needed":
                st.session_state.workflow_questions = data.get("questions", [])
                st.session_state.workflow_decision = None
            else:
                st.session_state.workflow_questions = []
                st.session_state.workflow_decision = data.get("decision")

            st.rerun()

        except Exception as e:
            st.error(f"Submission failed: {e}")

# --------------------------------------------------
# Audit trail (always shown when available)
# --------------------------------------------------
if st.session_state.workflow_audit:
    with st.expander("Workflow steps / audit trail", expanded=False):
        for step in st.session_state.workflow_audit:
            label = step.get("step", "step")
            ts = step.get("ts", "")
            detail = {k: v for k, v in step.items() if k not in ("step", "ts")}
            st.markdown(f"**{label}** `{ts}`")
            if detail:
                st.json(detail)

# --------------------------------------------------
# Clarification form
# --------------------------------------------------
if st.session_state.workflow_status == "clarification_needed":
    questions = st.session_state.workflow_questions
    st.warning(
        f"**Clarification required** — "
        f"please answer {len(questions)} question(s) before a decision can be made."
    )

    with st.form("clarification_form"):
        answers = {}
        for q in questions:
            q_id = q["id"]
            q_text = q["question"]
            exp_idx = q.get("expense_idx")
            label = q_text
            if exp_idx is not None:
                label = f"*Expense #{exp_idx + 1}* — {q_text}"

            if q.get("type") == "yes_no":
                answers[q_id] = st.radio(
                    label,
                    ["Yes", "No"],
                    key=f"clar_{q_id}",
                )
            else:
                answers[q_id] = st.text_area(
                    label,
                    key=f"clar_{q_id}",
                )

        submitted = st.form_submit_button("Submit Answers")

    if submitted:
        try:
            with st.spinner("Getting decision..."):
                resp = requests.post(
                    f"{BACKEND_URL}/claims/"
                    f"{st.session_state.claim_id}/answers",
                    json={"answers": answers},
                    timeout=120,
                )
            resp.raise_for_status()
            data = resp.json()

            st.session_state.workflow_status = data["status"]
            st.session_state.workflow_decision = data.get("decision")
            st.session_state.workflow_audit = data.get("audit_trail", [])
            st.session_state.workflow_questions = []
            st.rerun()

        except Exception as e:
            st.error(f"Failed to submit answers: {e}")

# --------------------------------------------------
# Decision display
# --------------------------------------------------
if st.session_state.workflow_status == "decided" and st.session_state.workflow_decision:
    dec = st.session_state.workflow_decision
    verdict = dec.get("decision", "")

    # Colour-coded banner
    colour_map = {
        "APPROVED": "success",
        "PARTIAL": "warning",
        "REJECTED": "error",
        "MANUAL_REVIEW": "info",
    }
    banner_fn = getattr(st, colour_map.get(verdict, "info"))
    banner_fn(f"### Decision: {verdict}")

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Approved",
        f"₹ {dec.get('approved_amount', 0):,.2f}",
    )
    m2.metric(
        "Rejected",
        f"₹ {dec.get('rejected_amount', 0):,.2f}",
    )
    approval_level = dec.get("approval_level", "auto")
    m3.metric("Approval Level", approval_level.upper())

    # Explanation
    if dec.get("explanation"):
        st.markdown("**Explanation**")
        st.write(dec["explanation"])

    # Policy references
    if dec.get("policy_references"):
        st.markdown("**Policy References**")
        st.write("  •  ".join(dec["policy_references"]))

    # Line-item breakdown
    line_items = dec.get("line_items", [])
    if line_items:
        with st.expander("Line-item breakdown", expanded=True):
            expenses_list = st.session_state.expenses
            for item in line_items:
                idx = item.get("expense_idx", 0)
                exp = (
                    expenses_list[idx]
                    if idx < len(expenses_list)
                    else {}
                )
                item_verdict = item.get("decision", "")
                item_colour = colour_map.get(item_verdict, "info")
                item_fn = getattr(st, item_colour)
                item_fn(
                    f"**{exp.get('vendor', f'Expense #{idx+1}')}** "
                    f"({exp.get('category', '')}) — "
                    f"{item_verdict}: "
                    f"approved ₹{item.get('approved_amount', 0):,.2f}, "
                    f"rejected ₹{item.get('rejected_amount', 0):,.2f}. "
                    f"_{item.get('reason', '')}_"
                )

    # Reset button
    st.markdown("---")
    if st.button("Start new claim"):
        for key in [
            "claim_id", "workflow_status", "workflow_questions",
            "workflow_decision", "workflow_audit", "expenses",
        ]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
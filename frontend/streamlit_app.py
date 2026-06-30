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
    "Taxi",
    "Bus",
    "Metro",
    "Meals",
    "Parking",
    "Internet",
    "Conference",
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
        "Upload upto 10 receipts",
        type=[
            "jpg",
            "jpeg",
            "png",
            "pdf"
        ],
        accept_multiple_files=True
    )

    if uploaded_files:

        if len(uploaded_files) > 10:
            st.error(
                "Maximum 10 receipts allowed."
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

                            parsed.append(
                                {
                                    "receipt_name":
                                        file.name,
                                    "category":
                                        ocr.get(
                                            "category",
                                            "Others"
                                        ),
                                    "vendor":
                                        ocr.get(
                                            "vendor",
                                            ""
                                        ),
                                    "amount":
                                        float(
                                            ocr.get(
                                                "amount",
                                                0
                                            )
                                        ),
                                    "date":
                                        ocr.get(
                                            "date",
                                            date.today()
                                            .strftime(
                                                "%d-%m-%Y"
                                            )
                                        ),
                                    "other_category":
                                        ""
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

        with st.container(
            border=True
        ):

            h1, h2 = st.columns(
                [10, 1]
            )

            with h1:

                title = (
                    expense
                    .get(
                        "receipt_name",
                        f"Expense "
                        f"{idx+1}"
                    )
                )

                st.markdown(
                    f"### {title}"
                )

            with h2:

                if st.button(
                    "🗑️",
                    key=f"del_{idx}"
                ):
                    delete_index = idx

            c1, c2 = st.columns(2)

            with c1:

                current = (
                    expense[
                        "category"
                    ]
                    if expense[
                        "category"
                    ]
                    in CATEGORIES
                    else "Others"
                )

                expense[
                    "category"
                ] = st.selectbox(
                    "Category",
                    CATEGORIES,
                    index=CATEGORIES
                    .index(
                        current
                    ),
                    key=f"cat_{idx}"
                )

                if (
                    expense[
                        "category"
                    ]
                    == "Others"
                ):

                    expense[
                        "other_category"
                    ] = st.text_input(
                        "Specify Category",
                        value=expense
                        .get(
                            "other_category",
                            ""
                        ),
                        key=f"other_{idx}"
                    )

                expense[
                    "amount"
                ] = st.number_input(
                    "Amount",
                    value=float(
                        expense[
                            "amount"
                        ]
                    ),
                    format="%.2f",
                    step=None,
                    key=f"amt_{idx}"
                )

            with c2:

                expense[
                    "vendor"
                ] = st.text_input(
                    "Vendor",
                    value=expense[
                        "vendor"
                    ],
                    key=f"vendor_{idx}"
                )

                current_date = (
                    datetime
                    .strptime(
                        expense[
                            "date"
                        ],
                        "%d-%m-%Y"
                    )
                    .date()
                )

                selected = (
                    st.date_input(
                        "Date",
                        value=current_date,
                        format="DD/MM/YYYY",
                        key=f"date_{idx}"
                    )
                )

                expense[
                    "date"
                ] = (
                    selected
                    .strftime(
                        "%d-%m-%Y"
                    )
                )

    if delete_index is not None:

        st.session_state.expenses.pop(
            delete_index
        )

        st.rerun()

    st.markdown("")

    if st.button(
        "➕ Add Expense Item"
    ):

        st.session_state.expenses.append(
            {
                "receipt_name":
                    "Manual Entry",
                "category":
                    "Hotel",
                "vendor":
                    "",
                "amount":
                    0.0,
                "date":
                    date.today()
                    .strftime(
                        "%d-%m-%Y"
                    ),
                "other_category":
                    ""
            }
        )

        st.rerun()

# ==================================================
# SUBMIT
# ==================================================
st.markdown("---")

_, _, submit = st.columns(
    [5, 1, 1]
)

with submit:

    if st.button(
        "Submit Claim",
        type="primary",
        use_container_width=True
    ):

        errors = validate_claim(
            employee_id,
            st.session_state
            .expenses
        )

        if errors:

            st.error(
                "Please fix the following:"
            )

            for e in errors:
                st.write(
                    f"• {e}"
                )

        else:

            payload = {
                "employee_id":
                    employee_id,
                "expenses":
                    st.session_state
                    .expenses
            }

            try:

                response = requests.post(
                    f"{BACKEND_URL}/submit",
                    json=payload
                )

                st.success(
                    "Claim submitted"
                )

                st.json(
                    response.json()
                )

            except Exception as e:

                st.error(
                    str(e)
                )
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


VECTOR_DB_DIR = "vectorDB/chroma"

embeddings = OllamaEmbeddings(
    model="nomic-embed-text"
)

db = Chroma(
    persist_directory=VECTOR_DB_DIR,
    embedding_function=embeddings
)


print(
    "\nTotal documents:",
    db._collection.count()
)

queries = [

    # Restaurant bill with alcohol
    {
        "name":
            "Restaurant + Alcohol",

        "query":
            """
            Expense Category:
            Meals

            Amount:
            3280

            Findings:
            - alcohol detected
            - multiple attendees likely

            Determine applicable reimbursement
            policies, approval requirements,
            clarification questions,
            exceptions and decision rules.
            """
    },

    # Luxury hotel
    {
        "name":
            "Luxury Hotel",

        "query":
            """
            Expense Category:
            Hotel

            Hotel:
            JW Marriott

            Amount:
            18000

            Determine applicable reimbursement
            policies and required approvals.
            """
    },

    # Meal exceeding limit
    {
        "name":
            "Meal Limit",

        "query":
            """
            Expense Category:
            Meals

            Amount:
            2750

            Findings:
            - exceeds meal limit

            Determine applicable policies.
            """
    },

    # High taxi fare
    {
        "name":
            "Taxi Expense",

        "query":
            """
            Expense Category:
            Travel

            Expense Type:
            Taxi

            Amount:
            6200

            Determine reimbursement
            policies and approvals.
            """
    },

    # International travel
    {
        "name":
            "International Travel",

        "query":
            """
            Expense Category:
            International Travel

            Destination:
            Germany

            Expenses:
            Hotel
            Meals
            Taxi

            Determine applicable
            reimbursement policies.
            """
    },

    # Emergency hotel booking
    {
        "name":
            "Emergency Expense",

        "query":
            """
            Emergency travel due to
            flight cancellation.

            Hotel expense:
            15000

            Determine emergency
            reimbursement policies.
            """
    }
]


# ==================================================
# RETRIEVAL TESTING
# ==================================================
for item in queries:

    print("\n")
    print("=" * 100)
    print(
        "TEST:",
        item["name"]
    )
    print("=" * 100)
    print("\nQUERY:\n")
    print(item["query"])
    docs = db.similarity_search(
        item["query"],
        k=5
    )
    print("\n")
    print(
        f"Retrieved "
        f"{len(docs)} "
        f"documents"
    )
    for idx, doc in enumerate(
        docs
    ):
        print("\n")
        print(
            "-" * 80
        )

        print(
            f"RESULT "
            f"{idx+1}"
        )

        print(
            "-" * 80
        )

        source = (
            doc.metadata.get(
                "source",
                "Unknown"
            )
        )
        category = (
            doc.metadata.get(
                "category",
                "Unknown"
            )
        )
        policy = (
            doc.metadata.get(
                "policy_id",
                "Unknown"
            )
        )
        print(
            "SOURCE:",
            source
        )
        print(
            "CATEGORY:",
            category
        )
        print(
            "POLICY:",
            policy
        )
        print(
            "\nCONTENT:\n"
        )
        print(
            doc.page_content
        )
        print("\n")
from rag.retriever import retrieve_policy


def lookup_policy(category: str, context: str = "") -> list:
    query = f"{category} {context}".strip()
    return retrieve_policy(query)

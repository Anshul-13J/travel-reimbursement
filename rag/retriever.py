import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", str(ROOT / "vectorDB/chroma"))
POLICY_DIR = os.getenv("POLICY_DIR", str(ROOT / "policies"))


def retrieve_policy(query: str, k: int = 5) -> list:
    """
    Query ChromaDB for relevant policy chunks.
    Falls back to keyword search over markdown files if the vector DB is unavailable.
    """
    try:
        from langchain_chroma import Chroma
        from langchain_ollama.embeddings import OllamaEmbeddings

        if not Path(VECTOR_DB_DIR).exists():
            return _keyword_fallback(query, k)

        embeddings = OllamaEmbeddings(
            model=os.getenv("EMBED_MODEL", "nomic-embed-text")
        )
        vectorstore = Chroma(
            persist_directory=VECTOR_DB_DIR,
            embedding_function=embeddings,
        )
        docs = vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
    except Exception:
        return _keyword_fallback(query, k)


def _keyword_fallback(query: str, k: int = 5) -> list:
    """Simple keyword match over policy markdown files."""
    keywords = query.lower().split()
    results = []

    policy_dir = Path(POLICY_DIR)
    if not policy_dir.exists():
        return []

    for md_file in sorted(policy_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            score = sum(1 for kw in keywords if kw in text.lower())
            if score > 0:
                results.append((score, text[:1500]))
        except Exception:
            continue

    results.sort(reverse=True)
    return [text for _, text in results[:k]]

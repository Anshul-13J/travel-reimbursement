"""
Run this once to build the ChromaDB vector index from policy markdown files.
Usage: python rag/build_index.py
"""
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
POLICY_DIR = str(ROOT / "policies")
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", str(ROOT / "vectorDB/chroma"))


def build_vector_db():
    from langchain_community.document_loaders import DirectoryLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_ollama.embeddings import OllamaEmbeddings
    from langchain_chroma import Chroma

    print("Loading policies...")
    loader = DirectoryLoader(POLICY_DIR, glob="**/*.md")
    docs = loader.load()
    print(f"Loaded {len(docs)} docs")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
    )
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")

    embeddings = OllamaEmbeddings(
        model=os.getenv("EMBED_MODEL", "nomic-embed-text")
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTOR_DB_DIR,
    )

    print("Vector DB built at:", VECTOR_DB_DIR)
    print("Total chunks stored:", vectorstore._collection.count())


if __name__ == "__main__":
    build_vector_db()

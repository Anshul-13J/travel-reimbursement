from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma


POLICY_DIR = "policies"
VECTOR_DB_DIR = (
    "vectorDB/chroma"
)

def build_vector_db():
    print(
        "Loading policies..."
    )
    loader = DirectoryLoader(
        POLICY_DIR,
        glob="**/*.md"
    )
    docs = loader.load()
    print(
        f"Loaded "
        f"{len(docs)} docs"
    )
    splitter = (
        RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100
        )
    )
    chunks = splitter.split_documents(
        docs
    )
    print(
        f"Created "
        f"{len(chunks)} chunks"
    )
    embeddings = (
        OllamaEmbeddings(
            model=
                "nomic-embed-text"
        )
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=
            VECTOR_DB_DIR
    )

    print(
        "Vector DB created"
    )

    print(
        vectorstore
        ._collection
        .count()
    )


if __name__ == "__main__":
    build_vector_db()
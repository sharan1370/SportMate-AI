from src.rag.embeddings import EmbeddingModel
from src.rag.loader import load_documents
from src.rag.splitter import split_documents
from src.rag.vectorstore import VectorStore


def ingest_knowledge_base() -> None:
    """Build the SportMate knowledge-base vector store."""

    print("Loading documents...")

    documents = load_documents()

    print(
        f"Documents loaded: {len(documents)}"
    )

    print("Splitting documents...")

    chunks = split_documents(documents)

    print(
        f"Chunks created: {len(chunks)}"
    )

    print("Loading embedding model...")

    embedding_model = EmbeddingModel()

    print("Generating embeddings...")

    embeddings = embedding_model.embed_documents(
        [
            chunk["content"]
            for chunk in chunks
        ]
    )

    print("Saving to Chroma...")

    vector_store = VectorStore()

    vector_store.add_documents(
        chunks=chunks,
        embeddings=embeddings,
    )

    print("Knowledge base ingestion completed.")


if __name__ == "__main__":
    ingest_knowledge_base()
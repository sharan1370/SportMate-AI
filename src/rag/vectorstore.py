from pathlib import Path

import chromadb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VECTORSTORE_DIR = PROJECT_ROOT / "vectorstore" / "chroma"
COLLECTION_NAME = "sportmate_knowledge"


class VectorStore:
    """Chroma vector store for SportMate knowledge."""

    def __init__(
        self,
        persist_directory: Path = VECTORSTORE_DIR,
    ):
        persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = chromadb.PersistentClient(
            path=str(persist_directory)
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": (
                        "SportMate policy knowledge base"
                    )
                },
            )
        )

    def add_documents(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Store document chunks and embeddings."""

        if not chunks:
            return

        self.collection.upsert(
            ids=[
                chunk["chunk_id"]
                for chunk in chunks
            ],
            embeddings=embeddings,
            documents=[
                chunk["content"]
                for chunk in chunks
            ],
            metadatas=[
                {
                    "source": chunk["source"],
                }
                for chunk in chunks
            ],
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """Search for the most relevant chunks."""

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        matches = []

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances,
        ):
            matches.append(
                {
                    "content": document,
                    "source": metadata["source"],
                    "distance": distance,
                }
            )

        return matches
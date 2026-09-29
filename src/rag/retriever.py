from src.rag.embeddings import EmbeddingModel
from src.rag.vectorstore import VectorStore


class Retriever:
    """Retrieve relevant SportMate policy information."""

    def __init__(
        self,
        top_k: int = 5,
        distance_threshold: float = 1.4,
    ):
        self.top_k = top_k
        self.distance_threshold = distance_threshold

        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore()

    def retrieve(
        self,
        query: str,
    ) -> list[dict]:
        """Retrieve only relevant knowledge-base chunks."""

        query_embedding = (
            self.embedding_model.embed_query(query)
        )

        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=self.top_k,
        )

        relevant_results = [
            result
            for result in results
            if result["distance"] <= self.distance_threshold
        ]

        return relevant_results
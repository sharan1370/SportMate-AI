from src.rag.retriever import Retriever


# Load once and reuse for faster responses
_retriever = Retriever(
    top_k=3,
    distance_threshold=1.4,
)


def search_policy(query: str) -> dict:
    """
    Search the SportMate knowledge base for information
    relevant to the user's question.
    """

    if not query or not query.strip():
        return {
            "success": False,
            "message": "Please provide a question.",
        }

    results = _retriever.retrieve(query.strip())

    if not results:
        return {
            "success": False,
            "message": "Answer not found in the SportMate knowledge base.",
        }

    return {
        "success": True,
        "query": query,
        "results": [
            {
                "source": result["source"],
                "content": result["content"],
                "distance": result["distance"],
            }
            for result in results
        ],
    }
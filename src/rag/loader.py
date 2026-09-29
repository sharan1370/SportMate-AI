from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"


def load_documents() -> list[dict]:
    """
    Load all text documents from the knowledge base.

    Returns:
        A list of dictionaries containing:
        - source
        - content
    """

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge base directory not found: "
            f"{KNOWLEDGE_BASE_DIR}"
        )

    documents = []

    for file_path in sorted(
        KNOWLEDGE_BASE_DIR.glob("*.txt")
    ):
        content = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            continue

        documents.append(
            {
                "source": file_path.name,
                "content": content,
            }
        )

    if not documents:
        raise ValueError(
            "No knowledge-base documents were found."
        )

    return documents
from src.rag.loader import load_documents
from src.rag.splitter import split_documents
from src.rag.retriever import Retriever


def test_loader_finds_knowledge_base_documents():
    documents = load_documents()

    assert len(documents) == 5

    sources = {doc["source"] for doc in documents}

    assert "cancellation_policy.txt" in sources
    assert "equipment_rental.txt" in sources
    assert "membership.txt" in sources
    assert "opening_hours_and_rules.txt" in sources
    assert "pricing_and_payment.txt" in sources


def test_splitter_creates_chunks():
    documents = load_documents()
    chunks = split_documents(documents)

    assert len(chunks) > len(documents)

    for chunk in chunks:
        assert "content" in chunk
        assert "source" in chunk
        assert "chunk_id" in chunk
        assert chunk["content"].strip()


def test_retriever_returns_relevant_results():
    retriever = Retriever(
        top_k=1,
        distance_threshold=1.4,
    )

    questions = [
        "How long before a booking can I cancel for a full refund?",
        "How much does a badminton racket cost?",
        "What are the membership benefits?",
        "What are the opening hours for badminton courts?",
        "How much does football cost per hour?",
    ]

    for question in questions:
        results = retriever.retrieve(question)

        assert results, f"No result returned for: {question}"


def test_retriever_rejects_unrelated_questions():
    retriever = Retriever(
        top_k=1,
        distance_threshold=1.4,
    )

    questions = [
        "What is the capital of France?",
        "Who invented the telephone?",
        "How do I make pizza?",
        "What is Python programming?",
    ]

    for question in questions:
        results = retriever.retrieve(question)

        assert results == [], f"Unexpected result for: {question}"
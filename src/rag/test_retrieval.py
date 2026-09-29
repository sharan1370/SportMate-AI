from src.rag.retriever import Retriever


def main():
    print("Loading SportMate retriever...")

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
        "What is the capital of France?",
        "Who invented the telephone?",
        "How do I make pizza?",
        "What is Python programming?",
    ]

    for question in questions:
        results = retriever.retrieve(question)

        print("\n" + "=" * 70)
        print(f"Question: {question}")

        if not results:
            print("No result")
            continue

        result = results[0]

        print(f"Source:   {result['source']}")
        print(f"Distance: {result['distance']:.4f}")


if __name__ == "__main__":
    main()
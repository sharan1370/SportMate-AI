from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(
    documents: list[dict],
) -> list[dict]:
    """
    Split knowledge-base documents into chunks
    while preserving the source document.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
        ],
    )

    chunks = []

    for document in documents:

        split_texts = splitter.split_text(
            document["content"]
        )

        for index, text in enumerate(split_texts):

            chunks.append(
                {
                    "chunk_id": (
                        f"{document['source']}"
                        f"_{index}"
                    ),
                    "source": document["source"],
                    "content": text,
                }
            )

    return chunks
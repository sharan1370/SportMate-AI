from src.config.settings import GROQ_API_KEY, GROQ_MODEL
from langchain_groq import ChatGroq


llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0,
)


response = llm.invoke(
    "Say hello and confirm that you are connected to SportMate AI."
)

print("Groq connection successful!")
print("Model:", GROQ_MODEL)
print("Response:", response.content)
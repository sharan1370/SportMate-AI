from groq import Groq

from src.config.settings import GROQ_API_KEY, GROQ_MODEL


client = Groq(
    api_key=GROQ_API_KEY,
    max_retries=0,
)

response = client.chat.completions.create(
    model=GROQ_MODEL,
    messages=[
        {
            "role": "user",
            "content": "Say hello and confirm that you are working.",
        }
    ],
    temperature=0,
    max_tokens=200,
)

print("Model:", GROQ_MODEL)
print("Response:", response.choices[0].message.content)
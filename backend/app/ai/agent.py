from langchain_groq import ChatGroq

from app.config.settings import settings

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=settings.GROQ_API_KEY or "gsk_placeholder_key",
    temperature=0,
    request_timeout=6.0,
)
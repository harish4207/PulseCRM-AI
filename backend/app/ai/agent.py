from langchain_groq import ChatGroq

from app.config.settings import settings

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=settings.GROQ_API_KEY,
    temperature=0
)
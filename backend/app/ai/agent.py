import logging
from langchain_groq import ChatGroq
from app.config.settings import settings

logger = logging.getLogger(__name__)

try:
    llm = ChatGroq(
        model=settings.GROQ_MODEL or "openai/gpt-oss-120b",
        api_key=settings.GROQ_API_KEY or "gsk_placeholder_key",
        temperature=0,
        request_timeout=8.0,
    )
except Exception as e:
    logger.warning(f"[Agent] Could not initialize ChatGroq: {e}")
    llm = None
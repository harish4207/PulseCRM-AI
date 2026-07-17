from app.ai.agent import llm
from app.ai.tools import search_hcp

agent = llm.bind_tools([search_hcp])
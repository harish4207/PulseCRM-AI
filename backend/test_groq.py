from langchain_core.messages import HumanMessage

from app.ai.agent import llm

response = llm.invoke(
    [
        HumanMessage(
            content="Hello! Introduce yourself in one sentence."
        )
    ]
)

print(response.content)
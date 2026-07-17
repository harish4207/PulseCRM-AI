from langchain_core.messages import HumanMessage

from app.ai.agent import llm


def extract_meeting_details(text: str):

    prompt = f"""
You are an AI assistant for a Medical CRM.

Extract the following information.

Return ONLY valid JSON.

Fields:

doctor_name
hospital
products_discussed
follow_up_date
meeting_summary

IMPORTANT:
- Return ONLY valid JSON.
- follow_up_date MUST be in ISO 8601 datetime format.
- Example: 2026-07-22T10:00:00
- Never return values like "Tomorrow", "Tuesday", "Next Week", etc.
- If the exact date cannot be determined from the conversation, return null.

Conversation:

{text}
"""

    response = llm.invoke(
        [
            HumanMessage(content=prompt)
        ]
    )

    return response.content
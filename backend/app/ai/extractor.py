from langchain_core.messages import HumanMessage

from app.ai.agent import llm


def extract_meeting_details(text: str):

    prompt = f"""
You are an AI assistant for a Medical CRM.

Extract the following information from the meeting notes or transcript.

Return ONLY valid JSON.

Fields:
doctor_name: Full name of the doctor (e.g., "Dr. Rajesh Sharma" or "Dr Rajesh")
hospital: Hospital or clinic name (if mentioned, otherwise null)
specialization: Medical specialization (e.g., Cardiology, Oncology, if mentioned, otherwise null)
city: City or location (if mentioned, otherwise null)
phone: Phone number if explicitly mentioned in the transcript, otherwise null
email: Email address if explicitly mentioned in the transcript, otherwise null
products_discussed: Medications or products discussed (e.g., "CardioPress-50")
follow_up_date: Follow-up date/time in ISO 8601 datetime format if explicitly mentioned. If the transcript says a relative day such as "next Monday" without a time, convert it to the next matching weekday in ISO 8601 format using 00:00:00 if no time is provided. If no follow-up is mentioned, return null.
meeting_summary: Summary of the conversation and key medical discussion points.

IMPORTANT:
- Return ONLY valid JSON.
- Never fabricate doctor details, phone numbers, or emails.
- If exact information is not in the text, use null.
- Preserve explicit phone numbers, email addresses, and follow-up dates exactly when they are present.

Conversation:
{text}
"""

    response = llm.invoke(
        [
            HumanMessage(content=prompt)
        ]
    )

    return response.content
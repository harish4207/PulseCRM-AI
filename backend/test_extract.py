from app.ai.extractor import extract_meeting_details

meeting = """
I met Dr Sharma today at Apollo Hospital.

We discussed CardioPlus.

He liked the medicine.

He asked me to visit next Tuesday and bring a brochure.
"""

result = extract_meeting_details(meeting)

print(result)
import json

from app.ai.extractor import extract_meeting_details
from app.services.hcp_service import HCPService
from app.services.interaction_service import InteractionService
from app.schemas.interaction_schema import InteractionCreate


def process_meeting(db, meeting_text, user_id):

    # Step 1 - Extract meeting details
    extracted = extract_meeting_details(meeting_text)

    print("AI Output:")
    print("========================")
    print(extracted)
    print("========================")
    print(extracted)

    cleaned = (
    extracted
    .replace("```json", "")
    .replace("```", "")
    .strip()
)

    print(cleaned)

    data = json.loads(cleaned)

    # Step 2 - Find doctor
    doctors = HCPService.get_all_hcps(db)

    doctor = None

    for d in doctors:
        if d.doctor_name.lower() == data["doctor_name"].lower():
            doctor = d
            break

    if doctor is None:
        return {
            "success": False,
            "message": "Doctor not found."
        }

    # Step 3 - Create interaction object
    interaction = InteractionCreate(
        user_id=user_id,
        hcp_id=doctor.id,
        meeting_notes=data["meeting_summary"],
        products_discussed=data["products_discussed"],
        follow_up_date=data["follow_up_date"]
    )

    # Step 4 - Save interaction
    return InteractionService.create_interaction(
        db,
        interaction
    )
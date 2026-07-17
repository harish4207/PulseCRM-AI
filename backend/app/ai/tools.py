from langchain.tools import tool
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.hcp import HCP


@tool
def search_hcp(doctor_name: str):
    """
    Search for a doctor by name.
    """

    db: Session = SessionLocal()

    try:
        doctor = (
            db.query(HCP)
            .filter(HCP.doctor_name.ilike(f"%{doctor_name}%"))
            .first()
        )

        if not doctor:
            return "Doctor not found."

        return (
            f"Doctor: {doctor.doctor_name}, "
            f"Hospital: {doctor.hospital}, "
            f"City: {doctor.city}"
        )

    finally:
        db.close()
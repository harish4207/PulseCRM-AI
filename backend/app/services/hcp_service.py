from sqlalchemy.orm import Session

from app.models.hcp import HCP
from app.schemas.hcp_schema import HCPCreate
from app.schemas.hcp_schema import HCPCreate, HCPUpdate
from app.models.interaction import Interaction
from sqlalchemy.exc import IntegrityError

class HCPService:

    @staticmethod
    def create_hcp(db: Session, hcp: HCPCreate):

        # Check if email already exists
        existing_email = db.query(HCP).filter(HCP.email == hcp.email).first()

        if existing_email:
            return {
                "success": False,
                "message": "Doctor email already exists"
            }

        # Check if phone already exists
        existing_phone = db.query(HCP).filter(HCP.phone == hcp.phone).first()

        if existing_phone:
            return {
                "success": False,
                "message": "Doctor phone already exists"
            }

        # Create HCP object
        new_hcp = HCP(
            doctor_name=hcp.doctor_name,
            specialization=hcp.specialization,
            hospital=hcp.hospital,
            city=hcp.city,
            phone=hcp.phone,
            email=hcp.email
        )

        # Save to database
        db.add(new_hcp)
        db.commit()
        db.refresh(new_hcp)

        return {
            "success": True,
            "message": "Doctor added successfully",
            "doctor_id": new_hcp.id
        }

    @staticmethod
    def get_all_hcps(db: Session):

        doctors = db.query(HCP).all()

        return doctors
    @staticmethod
    def get_hcp_by_id(db: Session, hcp_id: int):

        doctor = db.query(HCP).filter(HCP.id == hcp_id).first()

        if not doctor:
            return {
                "success": False,
                "message": "Doctor not found"
            }

        return doctor
    @staticmethod
    def update_hcp(db: Session, hcp_id: int, hcp: HCPUpdate):

        doctor = db.query(HCP).filter(HCP.id == hcp_id).first()

        if not doctor:
            return {
                "success": False,
                "message": "Doctor not found"
            }

        doctor.doctor_name = hcp.doctor_name
        doctor.specialization = hcp.specialization
        doctor.hospital = hcp.hospital
        doctor.city = hcp.city
        doctor.phone = hcp.phone
        doctor.email = hcp.email

        db.commit()
        db.refresh(doctor)

        return {
            "success": True,
            "message": "Doctor updated successfully"
        }
    @staticmethod
    def delete_hcp(db: Session, hcp_id: int):

        doctor = db.query(HCP).filter(HCP.id == hcp_id).first()

        if not doctor:
            return {
                "success": False,
                "message": "Doctor not found"
            }

        # Prevent deletion if there are interactions referencing this HCP
        interaction_count = db.query(Interaction).filter(Interaction.hcp_id == hcp_id).count()
        if interaction_count > 0:
            return {
                "success": False,
                "message": "Cannot delete doctor with existing interactions"
            }

        try:
            db.delete(doctor)
            db.commit()
        except IntegrityError:
            db.rollback()
            return {
                "success": False,
                "message": "Failed to delete doctor due to database constraints"
            }

        return {
            "success": True,
            "message": "Doctor deleted successfully"
        }
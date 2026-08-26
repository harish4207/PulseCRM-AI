"""
seed_demo_data.py - Deterministic Demo Data Seeder for PulseCRM.

Cleans out temporary/synthetic test HCPs (e.g. Dr Phase4, Dr Temporary) and sets up
realistic healthcare professionals, interaction records, and scheduled follow-ups.
Safe to run multiple times (idempotent).
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app.database.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.hcp import HCP
from app.models.interaction import Interaction

def seed():
    db = SessionLocal()
    try:
        print("Starting deterministic demo data seeding...")

        # 1. Clean synthetic/temporary records
        temp_hcps = db.query(HCP).filter(
            (HCP.doctor_name.ilike("%Phase%")) |
            (HCP.doctor_name.ilike("%Temporary%")) |
            (HCP.doctor_name.ilike("%test%"))
        ).all()

        if temp_hcps:
            temp_ids = [h.id for h in temp_hcps]
            db.query(Interaction).filter(Interaction.hcp_id.in_(temp_ids)).delete(synchronize_session=False)
            db.query(HCP).filter(HCP.id.in_(temp_ids)).delete(synchronize_session=False)
            db.commit()
            print(f"Cleaned {len(temp_ids)} synthetic development HCP records.")

        # 2. Ensure Primary Test User exists
        primary_user = db.query(User).filter(User.email == "harish@gmail.com").first()
        if not primary_user:
            primary_user = User(
                email="harish@gmail.com",
                full_name="Harish (Pharma Rep)",
            )
            # Default password hash if needed
            from app.core.security import get_password_hash
            primary_user.hashed_password = get_password_hash("password123")
            db.add(primary_user)
            db.commit()
            db.refresh(primary_user)
            print(f"Created primary user: {primary_user.email} (ID: {primary_user.id})")
        else:
            print(f"Primary user verified: {primary_user.email} (ID: {primary_user.id})")

        # 3. Seed Realistic HCPs
        demo_hcps = [
            {
                "doctor_name": "Dr. Rajesh Kumar",
                "specialization": "Cardiologist",
                "hospital": "Apollo Hospital",
                "city": "Visakhapatnam",
                "phone": "9848022338",
                "email": "dr.rajesh@apollo.org",
            },
            {
                "doctor_name": "Dr. Sharma",
                "specialization": "Neurologist",
                "hospital": "Care Hospital",
                "city": "Hyderabad",
                "phone": "9848011223",
                "email": "dr.sharma@care.org",
            },
            {
                "doctor_name": "Dr. Priyanka",
                "specialization": "Oncologist",
                "hospital": "Apollo Hospital",
                "city": "Visakhapatnam",
                "phone": "9848033449",
                "email": "dr.priyanka@apollo.org",
            },
            {
                "doctor_name": "Dr. Ananya",
                "specialization": "Endocrinologist",
                "hospital": "KIMS Hospital",
                "city": "Hyderabad",
                "phone": "9848044550",
                "email": "dr.ananya@kims.org",
            },
            {
                "doctor_name": "Dr. Suresh Reddy",
                "specialization": "Orthopedic Surgeon",
                "hospital": "Manipal Hospital",
                "city": "Vijayawada",
                "phone": "9848055661",
                "email": "dr.suresh@manipal.org",
            },
        ]

        hcp_map = {}
        for h_data in demo_hcps:
            existing = db.query(HCP).filter(HCP.doctor_name == h_data["doctor_name"]).first()
            if not existing:
                # Check by email or phone to avoid unique constraint collisions
                existing = db.query(HCP).filter((HCP.phone == h_data["phone"]) | (HCP.email == h_data["email"])).first()
            if existing:
                existing.doctor_name = h_data["doctor_name"]
                existing.specialization = h_data["specialization"]
                existing.hospital = h_data["hospital"]
                existing.city = h_data["city"]
                existing.phone = h_data["phone"]
                existing.email = h_data["email"]
                db.commit()
                db.refresh(existing)
                hcp_map[h_data["doctor_name"]] = existing
            else:
                new_hcp = HCP(**h_data)
                db.add(new_hcp)
                db.commit()
                db.refresh(new_hcp)
                hcp_map[h_data["doctor_name"]] = new_hcp

        print(f"Seeded {len(hcp_map)} realistic demo HCPs:")
        for name, h in hcp_map.items():
            print(f"  - {h.doctor_name} | {h.specialization} | {h.hospital} ({h.city})")

        # 4. Seed Realistic Interactions & Scheduled Follow-ups
        now = datetime.now()
        demo_interactions = [
            {
                "doctor_name": "Dr. Rajesh Kumar",
                "meeting_notes": "Reviewed clinical study findings for CardioPress-50. Doctor expressed interest in prescribing for moderate hypertension patients and requested 10 sample packs.",
                "ai_summary": "Discussed CardioPress-50 trial efficacy. Doctor requested samples and scheduled follow-up.",
                "products_discussed": "CardioPress-50",
                "follow_up_date": now + timedelta(days=5),
            },
            {
                "doctor_name": "Dr. Priyanka",
                "meeting_notes": "Discussed CardioPress-50 cardiology research paper and clinical brochure. Doctor requested full clinical documentation for department review.",
                "ai_summary": "Product review for CardioPress-50. Doctor requested clinical brochure.",
                "products_discussed": "CardioPress-50",
                "follow_up_date": datetime(now.year, 9, 29, 10, 0, 0) if now.month <= 9 else datetime(now.year + 1, 9, 29, 10, 0, 0),
            },
            {
                "doctor_name": "Dr. Sharma",
                "meeting_notes": "Detailed discussion on NeuroCalm for chronic sleep disturbances and anxiety. Doctor reviewed dosage recommendations.",
                "ai_summary": "Detailed NeuroCalm clinical discussion.",
                "products_discussed": "NeuroCalm",
                "follow_up_date": None,
            },
            {
                "doctor_name": "Dr. Ananya",
                "meeting_notes": "Quarterly relationship visit. Introduced GlycoCare dual-action formulations for type-2 diabetes management.",
                "ai_summary": "GlycoCare introduction and quarterly review.",
                "products_discussed": "GlycoCare",
                "follow_up_date": now + timedelta(days=12),
            },
        ]

        for i_data in demo_interactions:
            doc_name = i_data.pop("doctor_name")
            hcp = hcp_map.get(doc_name)
            if not hcp:
                continue

            existing_int = db.query(Interaction).filter(
                Interaction.user_id == primary_user.id,
                Interaction.hcp_id == hcp.id
            ).first()

            if existing_int:
                existing_int.meeting_notes = i_data["meeting_notes"]
                existing_int.ai_summary = i_data["ai_summary"]
                existing_int.products_discussed = i_data["products_discussed"]
                existing_int.follow_up_date = i_data["follow_up_date"]
                db.commit()
            else:
                new_int = Interaction(
                    user_id=primary_user.id,
                    hcp_id=hcp.id,
                    **i_data
                )
                db.add(new_int)
                db.commit()

        print("Seeded realistic demo interactions and follow-ups successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    seed()

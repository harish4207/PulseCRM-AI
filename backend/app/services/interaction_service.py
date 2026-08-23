from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.schemas.interaction_schema import InteractionCreate
from app.models.hcp import HCP


class InteractionService:

    @staticmethod
    def create_interaction(
        db: Session,
        interaction: InteractionCreate
    ):

        # Verify HCP exists
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        if not hcp:
            return {
                "success": False,
                "message": "Referenced HCP not found"
            }

        new_interaction = Interaction(
            user_id=interaction.user_id,
            hcp_id=interaction.hcp_id,
            meeting_notes=interaction.meeting_notes,
            products_discussed=interaction.products_discussed,
            follow_up_date=interaction.follow_up_date
        )

        db.add(new_interaction)
        db.commit()
        db.refresh(new_interaction)

        return {
            "success": True,
            "message": "Interaction created successfully",
            "interaction_id": new_interaction.id
        }

    @staticmethod
    def get_interaction_by_id(db: Session, interaction_id: int):
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return None
        return interaction

    @staticmethod
    def get_interactions_by_user(db: Session, user_id: int):
        interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
        return interactions

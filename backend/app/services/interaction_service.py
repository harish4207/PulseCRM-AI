from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.schemas.interaction_schema import InteractionCreate


class InteractionService:

    @staticmethod
    def create_interaction(
        db: Session,
        interaction: InteractionCreate
    ):

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
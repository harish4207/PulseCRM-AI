from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.hcp_schema import HCPUpdate
from app.database.dependencies import get_db
from app.schemas.user_schema import UserRegister
from app.services.auth_impl import AuthService
from app.schemas.user_schema import UserRegister, UserLogin
from app.schemas.hcp_schema import HCPCreate
from app.services.hcp_service import HCPService
from app.schemas.interaction_schema import InteractionCreate
from app.services.interaction_service import InteractionService
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    return AuthService.register_user(db, user)
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    return AuthService.login_user(db, user)


@router.get('/me')
def me(current_user: User = Depends(get_current_user)):
    return {
        'id': current_user.id,
        'email': current_user.email,
        'full_name': current_user.full_name,
    }
@router.post("/hcps")
def create_hcp(hcp: HCPCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return HCPService.create_hcp(db, hcp)
@router.get("/hcps")
def get_all_hcps(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return HCPService.get_all_hcps(db)
@router.get("/hcps/{hcp_id}")
def get_hcp_by_id(hcp_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return HCPService.get_hcp_by_id(db, hcp_id)
@router.put("/hcps/{hcp_id}")
def update_hcp(
    hcp_id: int,
    hcp: HCPUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return HCPService.update_hcp(db, hcp_id, hcp)
@router.delete("/hcps/{hcp_id}")
def delete_hcp(
    hcp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = HCPService.delete_hcp(db, hcp_id)
    if not result.get("success"):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))
    return result
@router.post("/interactions")
def create_interaction(
    interaction: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Enforce that the interaction's user_id matches current user
    if interaction.user_id != current_user.id:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create interaction for another user")

    result = InteractionService.create_interaction(db, interaction)
    if not result.get("success"):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))

    return result


@router.get("/interactions")
def list_interactions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interactions = InteractionService.get_interactions_by_user(db, current_user.id)
    return interactions


@router.get("/interactions/{interaction_id}")
def get_interaction(interaction_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interaction = InteractionService.get_interaction_by_id(db, interaction_id)
    if not interaction:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
    if interaction.user_id != current_user.id:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this interaction")
    return interaction
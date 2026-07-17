from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.hcp_schema import HCPUpdate
from app.database.dependencies import get_db
from app.schemas.user_schema import UserRegister
from app.services.auth_service import AuthService
from app.schemas.user_schema import UserRegister, UserLogin
from app.schemas.hcp_schema import HCPCreate
from app.services.hcp_service import HCPService
from app.schemas.interaction_schema import InteractionCreate
from app.services.interaction_service import InteractionService
router = APIRouter()


@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    return AuthService.register_user(db, user)
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    return AuthService.login_user(db, user)
@router.post("/hcps")
def create_hcp(hcp: HCPCreate, db: Session = Depends(get_db)):
    return HCPService.create_hcp(db, hcp)
@router.get("/hcps")
def get_all_hcps(db: Session = Depends(get_db)):
    return HCPService.get_all_hcps(db)
@router.get("/hcps/{hcp_id}")
def get_hcp_by_id(hcp_id: int, db: Session = Depends(get_db)):
    return HCPService.get_hcp_by_id(db, hcp_id)
@router.put("/hcps/{hcp_id}")
def update_hcp(
    hcp_id: int,
    hcp: HCPUpdate,
    db: Session = Depends(get_db)
):
    return HCPService.update_hcp(db, hcp_id, hcp)
@router.delete("/hcps/{hcp_id}")
def delete_hcp(
    hcp_id: int,
    db: Session = Depends(get_db)
):
    return HCPService.delete_hcp(db, hcp_id)
@router.post("/interactions")
def create_interaction(
    interaction: InteractionCreate,
    db: Session = Depends(get_db)
):
    return InteractionService.create_interaction(db, interaction)
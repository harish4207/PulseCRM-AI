from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User
from app.schemas.user_schema import UserRegister, UserLogin
from app.core.security import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    @staticmethod
    def register_user(db: Session, user: UserRegister):

        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user.email).first()

        if existing_user:
            return {"success": False, "message": "Email already registered"}

        # Hash Password
        hashed_password = pwd_context.hash(user.password)

        # Create User Object
        new_user = User(
            full_name=user.full_name,
            email=user.email,
            password=hashed_password
        )

        # Save to Database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "success": True,
            "message": "User Registered Successfully"
        }

    @staticmethod
    def login_user(db: Session, user: UserLogin):

        existing_user = db.query(User).filter(
            User.email == user.email
        ).first()

        if not existing_user:
            return {
                "success": False,
                "message": "Invalid email or password"
            }

        if not pwd_context.verify(
            user.password,
            existing_user.password
        ):
            return {
                "success": False,
                "message": "Invalid email or password"
            }

        token = create_access_token(
            {
                "sub": existing_user.email,
                "id": existing_user.id
            }
        )

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer"
        }
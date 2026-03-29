"""Auth endpoints — signup and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session as DBSession

from app.core.auth import create_token, get_current_user, hash_password, verify_password
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest, db: DBSession = Depends(get_db)):
    """Create a new lecturer account."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    return AuthResponse(
        token=token,
        user={"id": user.id, "email": user.email, "name": user.name},
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: DBSession = Depends(get_db)):
    """Log in and receive a JWT token."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_token(user.id)
    return AuthResponse(
        token=token,
        user={"id": user.id, "email": user.email, "name": user.name},
    )


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return {"data": {"id": user.id, "email": user.email, "name": user.name}}

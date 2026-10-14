
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserLogin, UserOut, Token
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.dependencies import get_current_user

router = APIRouter()


# User registration
@router.post("/register", response_model=UserOut)
def register(data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# User login
@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user or not verify_password(
        data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "token_type": "bearer"
    }


# View profile
@router.get("/profile", response_model=UserOut)
def profile(user: User = Depends(get_current_user)):
    return user


# Update profile
@router.put("/profile", response_model=UserOut)
def update_profile(
    username: str | None = None,
    email: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if username is not None:
        username = username.strip()

        if not username:
            raise HTTPException(
                status_code=422,
                detail="Username cannot be empty"
            )

        user.username = username

    if email is not None:
        email = email.strip().lower()

        if not email or "@" not in email:
            raise HTTPException(
                status_code=422,
                detail="Please enter a valid email"
            )

        existing_user = db.query(User).filter(
            User.email == email,
            User.id != user.id
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        user.email = email

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update profile"
        )

    return user


# Swagger login
@router.post("/token", response_model=Token)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "token_type": "bearer"
    }


# Change password request schema
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


# Change password
@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not verify_password(
        data.current_password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    if verify_password(
        data.new_password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=400,
            detail="New password must be different"
        )

    user.hashed_password = hash_password(data.new_password)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not change password"
        )

    return {"message": "Password changed successfully"}

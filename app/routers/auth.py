from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserLogin, UserOut, Token
from app.security import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user

from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter()

@router.post("/register", response_model=UserOut)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(username=data.username, email=data.email, hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}

@router.get("/profile", response_model=UserOut)
def profile(user: User = Depends(get_current_user)):
    return user

@router.put("/profile")
def update_profile(
    username: str | None = None,
    email: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Update username if provided
    if username is not None:
        username = username.strip()

        if not username:
            raise HTTPException(
                status_code=422,
                detail="Username cannot be empty"
            )

        user.username = username

    # Update email if provided
    if email is not None:
        email = email.strip().lower()

        if not email:
            raise HTTPException(
                status_code=422,
                detail="Email cannot be empty"
            )

        existing_user = (
            db.query(User)
            .filter(
                User.email == email,
                User.id != user.id
            )
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        user.email = email

    db.commit()
    db.refresh(user)

    return user


@router.post("/token", response_model=Token)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == form_data.username)
        .first()
    )

    if not user or not verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "access_token": create_access_token(
            {"sub": str(user.id)}
        ),
        "token_type": "bearer"
    }


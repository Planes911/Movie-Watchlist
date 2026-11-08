"""Authentication endpoints: register and login."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import Api_Error
from app.models import User
from app.schemas import Login_In, Register_In, Token_Out, User_Out
from app.security import (
    burn_time_like_a_real_check,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register", response_model=User_Out, status_code=201)
def register(payload: Register_In, db: Session = Depends(get_db)):
    """Create a new account. Answers 409 if the email is already registered."""
    # Emails are case-insensitive: normalise before storing or comparing.
    email = payload.email.lower()

    # Friendly pre-check; the unique index on email is the real guarantee.
    if db.scalar(select(User.id).where(User.email == email)):
        raise Api_Error(409, "Email sudah terdaftar.")

    user = User(username=payload.username, email=email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two simultaneous registrations can both pass the check above; the unique index rejects the second.
        db.rollback()
        raise Api_Error(409, "Email sudah terdaftar.")
    db.refresh(user)
    # User_Out leaves out password_hash, so the hash never leaves the server.
    return user

@router.post("/login", response_model=Token_Out)
def login(payload: Login_In, db: Session = Depends(get_db)):
    """Verify credentials and return a JWT together with the user's public profile."""
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    if user is None:
        # Unknown email: still spend the time of a real password check so response time does not
        # reveal which emails are registered.
        burn_time_like_a_real_check(payload.password)
        raise Api_Error(401, "Email atau password salah.")
    # Same message as for an unknown email, so the response never reveals which part was wrong.
    if not verify_password(payload.password, user.password_hash):
        raise Api_Error(401, "Email atau password salah.")

    return Token_Out(token=create_access_token(user.id), user=User_Out.model_validate(user))

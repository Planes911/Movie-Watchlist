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
    email = payload.email.lower()

    if db.scalar(select(User.id).where(User.email == email)):
        raise Api_Error(409, "Email sudah terdaftar.")

    user = User(username=payload.username, email=email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Api_Error(409, "Email sudah terdaftar.")
    db.refresh(user)
    return user

@router.post("/login", response_model=Token_Out)
def login(payload: Login_In, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    if user is None:
        burn_time_like_a_real_check(payload.password)
        raise Api_Error(401, "Email atau password salah.")
    if not verify_password(payload.password, user.password_hash):
        raise Api_Error(401, "Email atau password salah.")

    return Token_Out(token=create_access_token(user.id), user=User_Out.model_validate(user))
                    
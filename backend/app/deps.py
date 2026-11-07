import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import Api_Error
from app.models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False, description="Tempel JWT danri /api/auth/logi")

_WWW_AUTH = {"WWW-Authenticate": "Bearer"}

def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise Api_Error(401, "Token autentikasi tidak ditemukan. Login terlebih dahulu.", _WWW_AUTH)
    try:
        user_id = decode_access_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise Api_Error(401, "Token sudah kedaluwarsa. Silakan login ulang.", _WWW_AUTH)
    except (jwt.PyJWTError, ValueError):
        raise Api_Error(401, "Token tidak valid.", _WWW_AUTH)

    user = db.get(User, user_id)
    if user is None:  # token valid tapi akun sudah dihapus
        raise Api_Error(401, "Pengguna untuk token ini tidak ditemukan.", _WWW_AUTH)
    return user
import datetime
import secrets
import logging

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from config import settings
from db import get_config, set_config

logger = logging.getLogger(__name__)
router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def _get_jwt_secret() -> str:
    secret = get_config("jwt_secret")
    if not secret:
        secret = secrets.token_hex(32)
        set_config("jwt_secret", secret)
    return secret


def _get_admin_hash() -> str:
    stored = get_config("admin_password_hash")
    if not stored:
        password = settings.auth.admin_password or "admin"
        stored = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        set_config("admin_password_hash", stored)
        logger.info("Admin password hash initialized.")
    return stored


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            _get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if req.username != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    admin_hash = _get_admin_hash()
    if not bcrypt.checkpw(req.password.encode(), admin_hash.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_token(req.username)
    return LoginResponse(token=token, username=req.username)


@router.post("/logout")
async def logout(_user: str = Depends(require_auth)):
    return {"message": "Logged out"}

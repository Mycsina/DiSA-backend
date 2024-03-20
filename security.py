from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from storage.user import get_user_by_id

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "ThIsIsAsEcReTkEy"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return decoded_token


def verify_user(user_id: UUID, token: str):
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    decoded_token = decode_token(token)
    if decoded_token != user.token:
        raise HTTPException(status_code=404, detail="Authentication failed")

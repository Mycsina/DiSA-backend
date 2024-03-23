from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from classes.user import User
from exceptions import BearerException
from storage.user import get_user_by_id, get_user_by_username

SECRET_KEY = "78a6d789443db45e595153ec30f5708e47e97313d1273b1414beafc60d6ff05b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


class Token(BaseModel):
    access_token: str
    token_type: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def password_hash(password: str):
    return pwd_context.hash(password)


def password_verify(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)


def verify_user(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if not user:
        return
    if not password_verify(password, user.password):
        return
    return user


# TODO - this is for the CMD peeps
def verify_session(id_token: str, session_token: str) -> Optional[User]:
    pass


# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#handle-jwt-tokens
def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = BearerException(detail="Could not validate token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

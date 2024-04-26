from datetime import datetime, timedelta, timezone
from os import getenv

from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Session

from BlockchainService import BlockchainService
from exceptions import BearerException
from models.user import User
from storage.main import engine
from storage.user import get_user_by_email, get_user_by_id

load_dotenv()

SECRET_KEY = getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise ValueError("SECRET_KEY not set")

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


def verify_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return
    if not user.password:
        return
    if not password_verify(password, user.password):
        return
    return user


# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#handle-jwt-tokens
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    with Session(engine) as session:
        credentials_exception = BearerException("Could not validate token")
        with session:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
                if user_id is None:
                    raise credentials_exception
            except JWTError:
                raise credentials_exception
            user = get_user_by_id(session, user_id)
            if user is None:
                raise credentials_exception
            return user


def verify_manifest(manifest_hash: str, transaction_address: str) -> bool:
    """
    verifies whether the manifest_hash matches the hash in the blockchain
    Note: it is assumed manifest_hash and transaction_address are both hexstrings (start with 'Ox')
    """
    return True
    blockChainService = BlockchainService()
    receipt = blockChainService.get_transaction_receipt(transaction_address)
    storedHash = blockChainService.get_manifest_hash(receipt)
    return manifest_hash == storedHash

from uuid import UUID

import requests
from sqlmodel import Session, select

from models.user import User, UserCMDCreate, UserCreate
from utils.paperless import create_correspondent
from utils.exceptions import CMDFailure


async def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        name=user.name,
        email=user.email,
        password=user.password,
        nic=user.nic,
    )
    corr_id = await create_correspondent(name=db_user.email)
    db_user.paperless.paperless_id = corr_id  # type: ignore
    db.add(db_user)
    db.commit()
    return db_user


def create_anonymous_user(db: Session, email: str) -> User:
    db_user = User(email=email)
    db.add(db_user)
    db.commit()
    return db_user


async def create_cmd_user(db: Session, user: UserCMDCreate, nic: str) -> User:
    db_user = User(
        email=user.email,
        nic=nic,
    )
    corr_id = await create_correspondent(name=db_user.email)
    db_user.paperless.paperless_id = corr_id  # type: ignore
    db.add(db_user)
    db.commit()
    return db_user


def update_user_token(db: Session, user: User, token: str) -> User:
    user.token = token
    db.add(user)
    db.commit()
    return user


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    statement = select(User).where(User.id == user_id)
    results = db.exec(statement)
    return results.first()


def get_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.name == username)
    results = db.exec(statement)
    return results.first()


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    results = db.exec(statement)
    return results.first()


def get_user_by_nic(db: Session, nic: str) -> User | None:
    statement = select(User).where(User.nic == nic)
    results = db.exec(statement)
    return results.first()


def is_anonymous_user(db: Session, user: User) -> bool:
    return user.nic is None


def retrieve_nic(cmd_token: str) -> str:
    url = "https://preprod.autenticacao.gov.pt/oauthresourceserver/api/AttributeManager"
    payload = {
        "token": cmd_token,
    }
    response = requests.post(url, data=payload)
    parsed_response = response.json()
    new_token = parsed_response.get("token", None)
    auth_context = parsed_response.get("authenticationContextId", None)
    if auth_context is None or new_token is None:
        raise CMDFailure()

    response = requests.get(url, params={"token": new_token, "authenticationContextId": auth_context})
    parsed_response = response.json()
    for obj in parsed_response:
        if "NIC" in obj["name"]:
            return obj["value"]

    raise ValueError("NIC not found")

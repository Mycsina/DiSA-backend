import logging
import time
from typing import Tuple
from uuid import UUID

import requests
from sqlmodel import Session, select

import storage.paperless as ppl
from models.user import User, UserCMDCreate, UserCreate
from utils.exceptions import CMDFailure

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


async def create_user(db: Session, user: UserCreate) -> User:
    logger.debug(f"Creating user: {user.email}")
    db_user = User(
        name=user.name,
        email=user.email,
        password=user.password,
        nic=user.nic,
    )
    db.add(db_user)
    await ppl.create_user(db, db_user)
    db.commit()
    logger.debug(f"Created user successfully: {user.email}")
    return db_user


def create_anonymous_user(db: Session, email: str) -> User:
    logger.debug(f"Creating anonymous user: {email}")
    db_user = User(email=email)
    db.add(db_user)
    db.commit()
    logger.debug(f"Created anonymous user successfully: {email}")
    return db_user


async def create_cmd_user(db: Session, user: UserCMDCreate, nic: str, name: str) -> User:
    logger.debug(f"Creating CMD user: {user.email}")
    db_user = User(email=user.email, nic=nic, name=name)
    await ppl.create_user(db, db_user)
    db.commit()
    logger.debug(f"Created CMD user successfully: {user.email}")
    return db_user


def update_user_token(db: Session, user: User, token: str) -> User:
    logger.debug(f"Updating user token for {user.email}")
    user.token = token
    db.add(user)
    db.commit()
    logger.debug(f"Updated user token successfully for {user.email}")
    return user


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    logger.debug(f"Retrieving user by ID: {user_id}")
    statement = select(User).where(User.id == user_id)
    results = db.exec(statement)
    user = results.first()
    if user:
        logger.debug(f"User retrieved successfully by ID: {user_id}")
    else:
        logger.warning(f"User not found with ID: {user_id}")
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    logger.debug(f"Retrieving user by username: {username}")
    statement = select(User).where(User.name == username)
    results = db.exec(statement)
    user = results.first()
    if user:
        logger.debug(f"User retrieved successfully by username: {username}")
    else:
        logger.warning(f"User not found with username: {username}")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    logger.debug(f"Retrieving user by email: {email}")
    statement = select(User).where(User.email == email)
    results = db.exec(statement)
    user = results.first()
    if user:
        logger.debug(f"User retrieved successfully by email: {email}")
    else:
        logger.warning(f"User not found with email: {email}")
    return user


def get_user_by_nic(db: Session, nic: str) -> User | None:
    logger.debug(f"Retrieving user by NIC: {nic}")
    statement = select(User).where(User.nic == nic)
    results = db.exec(statement)
    user = results.first()
    if user:
        logger.debug(f"User retrieved successfully by NIC: {nic}")
    else:
        logger.warning(f"User not found with NIC: {nic}")
    return user


def is_anonymous_user(db: Session, user: User) -> bool:
    logger.debug(f"Checking if user is anonymous: {user.email}")
    is_anonymous = user.nic is None
    logger.debug(f"User is anonymous: {is_anonymous}")
    return is_anonymous


def retrieve_nic(cmd_token: str) -> Tuple[str, str]:
    logger.debug("Retrieving NIC from CMD token.")
    url = "https://preprod.autenticacao.gov.pt/oauthresourceserver/api/AttributeManager"
    payload = {
        "token": cmd_token,
        "attributesName": ["http://interop.gov.pt/MDC/Cidadao/NIC" "http://interop.gov.pt/MDC/Cidadao/NomeProprio"],
    }

    response = requests.post(url, data=payload)
    parsed_response = response.json()
    new_token = parsed_response.get("token", None)
    auth_context = parsed_response.get("authenticationContextId", None)

    if auth_context is None or new_token is None:
        logger.error("Failed to retrieve NIC for CMD token.")
        raise CMDFailure()

    retries = 0
    nic, name = None, None
    while retries < 10:
        response = requests.get(url, params={"token": new_token, "authenticationContextId": auth_context})
        parsed_response = response.json()

        for obj in parsed_response:
            if "NIC" in obj["name"]:
                nic = obj["value"]
            if "NomeProprio" in obj["name"]:
                name = obj["value"]

        if nic is not None and name is not None:
            logger.debug(f"NIC retrieved successfully: {nic}")
            return nic, name

        time.sleep(3)

    logger.error("Failed to retrieve NIC for CMD token.")
    raise ValueError("NIC not found")

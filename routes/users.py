import logging
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

import storage.user as users
from models.user import UserCMDCreate, UserCreate
from storage.main import engine
from utils.exceptions import BearerException, CMDFailure
from utils.security import Token, create_access_token, password_hash, verify_user

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

users_router = APIRouter(
    prefix="/users",
    tags=["users"],
)


# register user
@users_router.post("/")
async def register_user(user: UserCreate):
    with Session(engine) as session:
        user.password = password_hash(user.password)
        try:
            db_user = await users.create_user(session, user)
        except Exception as e:
            logger.error(f"Failing to register user: {e}")
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))
        # UUID is not serializable, so we convert it to a string
        token = create_access_token(data={"sub": str(db_user.id)})
        db_user = users.update_user_token(session, db_user, token)
        logger.info(f"User {db_user.name} created successfully.")
        return {"message": f"User {db_user.name} created successfully", "token": token}


# TODO - test this
@users_router.post("/cmd")
async def register_with_cmd(user: UserCMDCreate):
    with Session(engine) as session:
        try:
            nic, name = users.retrieve_nic(user.cmd_token)
            db_user = await users.create_cmd_user(session, user, nic, name)
            token = create_access_token(data={"sub": str(db_user.id)})
            users.update_user_token(session, db_user, token)
            logger.info(f"User {name} created successfully.")
            return {"message": f"User {name} created successfully.", "token": token}
        except Exception as e:
            logger.error(f"Failing to register user with CMD: {e}")
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))


@users_router.post("/login/")
async def login_with_user_password(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    with Session(engine) as session:
        user = verify_user(session, form_data.username, form_data.password)
        if user is None:
            logger.error("Invalid username or password.")
            raise BearerException()
        access_token = create_access_token(data={"sub": str(user.id)})
        users.update_user_token(session, user, access_token)
        logger.info(f"User {user.name} logged in successfully.")
        return Token(access_token=access_token, token_type="Bearer")


# TODO - test this
@users_router.get("/login/cmd")
async def login_with_cmd(id_token: str) -> Token:
    with Session(engine) as session:
        try:
            nic, name = users.retrieve_nic(id_token)
            user = users.get_user_by_nic(session, nic)
            if user is None:
                logger.error("User not found with CMD token.")
                raise CMDFailure()
            access_token = create_access_token(data={"sub": str(user.id)})
            users.update_user_token(session, user, access_token)
            logger.info(f"User {name} logged in successfully.")
            return Token(access_token=access_token, token_type="Bearer")
        except Exception as e:
            logger.error(f"Failing to login with CMD: {e}")
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, SQLModel
from sqlalchemy.exc import DBAPIError

import storage.collection as collections
import storage.user as users
from exceptions import BearerException, CMDFailure
from models.collection import Collection, SharedState
from models.user import UserBase as APIUser
from models.user import UserCMDCreate, UserCreate
from security import (
    Token,
    create_access_token,
    get_current_user,
    password_hash,
    verify_session,
    verify_user,
)
from storage.main import engine

app = FastAPI()


# TODO - this is deprecated, implement new way of creating tables at startup
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}


# TODO - test this
@app.post("/collections/")
async def create_collection(
    user: Annotated[APIUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    share_state: SharedState = SharedState.private,
    status_code=HTTPStatus.CREATED,
):
    with Session(engine) as session:
        name = file.filename
        data = await file.read()
        collection = collections.create_collection(session, name, data, user)

        return {"message": "Collection created successfully", "uuid": collection.id}


@app.get("/collections/")
async def get_all_collections(
    user: Annotated[APIUser, Depends(get_current_user)],
) -> list[Collection]:
    with Session(engine) as db:
        return collections.get_collections(db)


# TODO - test this
@app.put("/collections/{collection_uuid}/{doc_uuid}")
async def update_document(
    user: Annotated[APIUser, Depends(get_current_user)],
    collection_uuid: UUID,
    doc_uuid: UUID,
    file: UploadFile,
):
    with Session(engine) as session:
        doc = collections.get_collection_by_id(collection_uuid)
        if doc is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if doc.owner != user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this document")
        collections.update_collection(session, collection_uuid, doc_uuid, file)


# TODO - test this
@app.delete("/collections/{collection_uuid}")
async def delete_collection(
    user: Annotated[APIUser, Depends(get_current_user)],
    collection_uuid: str,
):
    with Session(engine) as session:
        doc = collections.get_collection_by_id(collection_uuid)
        if doc is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if doc.owner != user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        collections.delete_collection(session, collection_uuid)


# TODO - test this
@app.delete("/collections/{collection_uuid}/{doc_uuid}")
async def delete_document(
    user: Annotated[APIUser, Depends(get_current_user)],
    collection_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        doc = collections.get_collection_by_id(doc_uuid)
        if doc is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if doc.owner != user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        collections.delete_document(session, collection_uuid, doc_uuid)


# TODO - test this
# TODO - ability to search for a document specifically
@app.get("/collections/{collection_uuid}/search")
async def search_documents(
    user: Annotated[APIUser, Depends(get_current_user)],
    collection_uuid: UUID,
    query: str,
):
    with Session(engine) as session:
        pass


# TODO - test this
# TODO - ability to filter documents by type, size or owner
# filter documents by type, size or owner
@app.get("/collections/{collection_uuid}/filter")
async def filter_documents(
    user: Annotated[APIUser, Depends(get_current_user)],
    type: str | None = None,
    size: int | None = None,
    owner: str | None = None,
):
    with Session(engine) as session:
        pass


# TODO - test this
# TODO - get the history of a document
# get the history of a document
@app.get("/collections/{collection_uuid}/{doc_uuid}/history")
async def get_document_history(
    user: Annotated[APIUser, Depends(get_current_user)],
    collection_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        pass


# register user
@app.post("/users/")
async def register_user(user: UserCreate):
    with Session(engine) as session:
        user.password = password_hash(user.password)
        try:
            db_user = users.create_user(session, user)
        except Exception as e:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))
        # UUID is not serializable, so we convert it to a string
        token = create_access_token(data={"sub": str(db_user.id)})
        db_user = users.update_user_token(session, db_user, token)
        return {"message": f"User {db_user.name} created successfully", "token": token}


# TODO - test this
@app.post("/users/cmd")
async def register_with_cmd(user: UserCMDCreate):
    # TODO - implement this
    return HTTPException(status_code=HTTPStatus.NOT_IMPLEMENTED)
    with Session(engine) as session:
        user = users.create_cmd_user(session, user)
        token = create_access_token(data={"sub": user.id})
        user.token = token
        return {"message": f"User {user.mobile_key} created successfully", "token": token}


@app.get("/users/login/")
async def login_with_user_password(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    with Session(engine) as session:
        user = verify_user(session, form_data.username, form_data.password)
        if user is None:
            raise BearerException
        access_token = create_access_token(data={"sub": str(user.id)})
        users.update_user_token(session, user, access_token)
        return Token(access_token=access_token, token_type="Bearer")


# TODO - test this
@app.get("users/login/cmd")
async def login_with_cmd(id_token: str, session_token: str) -> Token:
    # TODO - implement this (verify_session)
    return HTTPException(status_code=HTTPStatus.NOT_IMPLEMENTED)
    with Session(engine) as session:
        user = verify_session(id_token, session_token)
        if user is None:
            raise CMDFailure
        access_token = create_access_token(data={"sub": user.user_id})
        users.update_user_token(session, user, access_token)
        return Token(access_token=access_token, token_type="Bearer")

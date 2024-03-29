import os
import shutil
from http import HTTPStatus
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, SQLModel

import storage.collection as collections
import storage.user as users
from exceptions import BearerException, CMDFailure
from models.collection import Collection, SharedState
from models.folder import FolderIntake
from models.user import User
from models.user import UserCMDCreate, UserCreate
from security import (
    Token,
    create_access_token,
    get_current_user,
    password_hash,
    verify_session,
    verify_user,
)
from storage.main import engine, TEMP_FOLDER

app = FastAPI()


# TODO - this is deprecated, implement new way of creating tables at startup
# https://fastapi.tiangolo.com/advanced/events/
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)


# TODO - this is deprecated, implement new way of cleaning up at shutdown
# https://fastapi.tiangolo.com/advanced/events/
@app.on_event("shutdown")
def on_shutdown():
    if os.path.exists(TEMP_FOLDER):
        # Remove the temporary folder and its contents
        shutil.rmtree(TEMP_FOLDER)


@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}


@app.post("/collections/")
async def create_collection(
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    share_state: SharedState = SharedState.private,
):
    with Session(engine) as session:
        name = file.filename
        if name is None:
            raise HTTPException(status_code=400, detail="No file name provided")
        data = await file.read()
        collection = collections.create_collection(session, name, data, user, share_state)

        return {"message": "Collection created successfully", "uuid": collection.id}


@app.get("/collections/")
async def get_all_collections(
    user: Annotated[User, Depends(get_current_user)],
) -> Sequence[Collection]:
    with Session(engine) as db:
        return collections.get_collections(db)


@app.get("/collections/{col_uuid}")
async def get_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> Collection:
    with Session(engine) as session:
        collection = collections.get_collection_by_id(session, col_uuid)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return collection


@app.get("/collections/{col_uuid}/hierarchy")
async def get_collection_hierarchy(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> FolderIntake:
    with Session(engine) as session:
        folder = collections.get_collection_hierarchy(session, col_uuid)
        if folder is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return folder


# TODO - test this
@app.put("/collections/{col_uuid}/{doc_uuid}")
async def update_document(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
    file: UploadFile,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user:
            raise HTTPException(status_code=403, detail="You are not the owner of this document")
        doc = collections.get_document_by_id(session, doc_uuid)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc not in col.documents:
            raise HTTPException(status_code=404, detail="Document not in the specified collection")
        data = await file.read()
        collections.update_document(session, col_uuid, doc_uuid, data)


# TODO - test this
@app.delete("/collections/{col_uuid}")
async def delete_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
):
    with Session(engine) as session:
        doc = collections.get_collection_by_id(session, col_uuid)
        if doc is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if doc.owner != user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        collections.delete_collection(session, col_uuid)


# TODO - test this
@app.delete("/documents/{doc_uuid}")
async def delete_document(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        doc = collections.get_collection_by_id(session, doc_uuid)
        if doc is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if doc.owner != user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        collections.delete_document(session, col_uuid, doc_uuid)


# TODO - test this
# TODO - ability to search for a document specifically
@app.get("/documents/search")
async def search_documents(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    query: str,
):
    with Session(engine) as session:
        pass


# TODO - test this
# TODO - ability to filter documents by type, size or owner
# filter documents by type, size or owner
@app.get("/documents/filter")
async def filter_documents(
    user: Annotated[User, Depends(get_current_user)],
    type: str | None = None,
    size: int | None = None,
    owner: str | None = None,
):
    with Session(engine) as session:
        pass


# TODO - test this
# TODO - get the history of a document
# get the history of a document
@app.get("/documents/{doc_uuid}/history")
async def get_document_history(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
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

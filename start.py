import os
import shutil
from http import HTTPStatus
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

import storage.collection as collections
import storage.user as users
from exceptions import BearerException, CMDFailure, IntegrityBreach
from models.collection import Collection, SharedState
from models.folder import FolderIntake
from models.user import User, UserCMDCreate, UserCreate
from security import (
    Token,
    create_access_token,
    get_current_user,
    password_hash,
    verify_user,
)
from storage.main import DB_URL, TEMP_FOLDER, TEST, engine

app = FastAPI()


# TODO - this is deprecated, implement new way of creating tables at startup
# https://fastapi.tiangolo.com/advanced/events/
@app.on_event("startup")
def on_startup():
    if TEST:
        db_path = DB_URL.split("///")[1]
        shutil.copy2(db_path, db_path + ".bak")
    SQLModel.metadata.create_all(engine)
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)


# TODO - this is deprecated, implement new way of cleaning up at shutdown
# https://fastapi.tiangolo.com/advanced/events/
@app.on_event("shutdown")
def on_shutdown():
    if TEST:
        db_path = DB_URL.split("///")[1]
        shutil.copy2(db_path + ".bak", db_path)
        os.remove(db_path + ".bak")
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


@app.get("/collections/")
async def get_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> Collection:
    with Session(engine) as session:
        collection = collections.get_collection_by_id(session, col_uuid)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return collection


@app.get("/collections/hierarchy")
async def get_collection_hierarchy(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> FolderIntake:
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        folder = collections.get_collection_hierarchy(session, col)
        if folder is None:
            raise HTTPException(status_code=404, detail="Collection hierarchy is corrupted")
        return folder


@app.put("/collections/")
async def update_document(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
    file: UploadFile,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid)
        doc = collections.get_document_by_id(session, doc_uuid)

        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user:
            raise HTTPException(status_code=403, detail="You are not the owner of this document")
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc not in col.documents:
            raise HTTPException(status_code=404, detail="Document not in the specified collection")

        data = await file.read()
        try:
            collections.update_document(session, user, col_uuid, doc_uuid, data)
        except IntegrityError:
            raise IntegrityBreach("Document update failed. Verify the document hasn't already been updated")
        if doc.next is None:
            raise HTTPException(status_code=500, detail="Document update failed")
        return {"message": "Document updated successfully", "update_uuid": doc.next.id}


# TODO - test this
@app.delete("/collections/")
async def delete_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        collections.delete_collection(session, col)


# TODO - test this
@app.delete("/documents/")
async def delete_document(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid)
        doc = collections.get_document_by_id(session, doc_uuid)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc not in col.documents:
            raise HTTPException(status_code=404, detail="Document not in the specified collection")
        collections.delete_document(session, doc)


@app.get("/documents/search")
async def search_documents(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    name: str,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        documents = collections.search_documents(session, col, name)
        if documents is None:
            raise HTTPException(status_code=404, detail="No documents found")
        return documents


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
    with Session(engine) as session:
        nic = users.retrieve_nic(user.cmd_token)
        db_user = users.create_cmd_user(session, user, nic)
        token = create_access_token(data={"sub": str(db_user.id)})
        users.update_user_token(session, db_user, token)
        return {"message": f"User {user.mobile_key} created successfully", "token": token}


@app.get("/users/login/")
async def login_with_user_password(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    with Session(engine) as session:
        user = verify_user(session, form_data.username, form_data.password)
        if user is None:
            raise BearerException()
        access_token = create_access_token(data={"sub": str(user.id)})
        users.update_user_token(session, user, access_token)
        return Token(access_token=access_token, token_type="Bearer")


# TODO - test this
@app.get("users/login/cmd")
async def login_with_cmd(id_token: str) -> Token:
    with Session(engine) as session:
        nic = users.retrieve_nic(id_token)
        user = users.get_user_by_nic(session, nic)
        if user is None:
            raise CMDFailure()
        access_token = create_access_token(data={"sub": user.id})
        users.update_user_token(session, user, access_token)
        return Token(access_token=access_token, token_type="Bearer")

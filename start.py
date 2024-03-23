from http import HTTPStatus
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordRequestForm

import storage.collection as collections
import storage.user as users
from classes.collection import Collection
from classes.commons import SharedState
from classes.user import User
from security import Token, create_access_token, verify_user, verify_session, get_current_user
from exceptions import BearerException

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}


@app.post("/collections/")
async def create_collection(
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    share_state: SharedState = SharedState.private,
    status_code=HTTPStatus.CREATED,
):
    name = file.filename
    data = await file.read()
    collection = collections.create_collection(name, data, user)

    return {"message": "Collection created successfully", "uuid": collection.id}


@app.get("/collections/")
async def get_all_collections() -> List[Collection]:
    return collections.get_collections()


@app.put("/collections/{collection_uuid}/{doc_uuid}")
async def update_document(
    user: Annotated[User, Depends(get_current_user)],
    collection_uuid: UUID,
    doc_uuid: UUID,
    file: UploadFile,
):
    doc = collections.get_collection_by_id(collection_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if doc.owner != user.id:
        raise HTTPException(status_code=403, detail="You are not the owner of this document")
    collections.update_collection(collection_uuid, doc_uuid, file)


@app.delete("/collections/{collection_uuid}")
async def delete_collection(
    user: Annotated[User, Depends(get_current_user)],
    collection_uuid: str,
):
    doc = collections.get_collection_by_id(collection_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if doc.owner != user.id:
        raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
    collections.delete_collection(collection_uuid)


@app.delete("/collections/{collection_uuid}/{doc_uuid}")
async def delete_document(
    user: Annotated[User, Depends(get_current_user)],
    collection_uuid: UUID,
    doc_uuid: UUID,
):
    doc = collections.get_collection_by_id(doc_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if doc.owner != user.id:
        raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
    collections.delete_document(collection_uuid, doc_uuid)


# TODO - ability to search for a document specifically
@app.get("/collections/{collection_uuid}/search")
async def search_documents(user: Annotated[User, Depends(get_current_user)], collection_uuid: UUID, query: str):
    pass


# TODO - ability to filter documents by type, size or owner
# filter documents by type, size or owner
@app.get("/collections/{collection_uuid}/filter")
async def filter_documents(
    user: Annotated[User, Depends(get_current_user)],
    type: Optional[str] = None,
    size: Optional[int] = None,
    owner: Optional[str] = None,
):
    pass


# TODO - get the history of a document
# get the history of a document
@app.get("/collections/{collection_uuid}/{doc_uuid}/history")
async def get_document_history(user: Annotated[User, Depends(get_current_user)], collection_uuid: UUID, doc_uuid: UUID):
    pass


# register user
@app.post("/users/")
async def register_user(username: str, email: str, oauth_token: str):
    user = users.create_user(username, email, oauth_token)
    token = create_access_token(data={"sub": user.id})
    user.token = token
    users.USERS.append(user)
    return {"message": f"User {username} created successfully", "token": token}


@app.get("/users/login/")
async def login_with_user_password(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = verify_user(form_data.username, form_data.password)
    if user is None:
        raise BearerException
    access_token = create_access_token(data={"sub": user.user_id})
    return Token(access_token=access_token, token_type="bearer")


@app.get("users/login/cmd")
async def login_with_cmd(id_token: str, session_token: str) -> Token:
    user = verify_session(id_token, session_token)
    if user is None:
        raise BearerException
    access_token = create_access_token(data={"sub": user.user_id})
    return Token(access_token=access_token, token_type="bearer")

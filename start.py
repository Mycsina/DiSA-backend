import io
from datetime import datetime
from http import HTTPStatus
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from classes.collection import Collection, Document
from classes.commons import SharedState
from classes.event import Event
from classes.user import User, UserRole
from security import create_access_token, decode_token, oauth2_scheme, verify_user
import storage.collection as collections
import storage.user as users

app = FastAPI()

documents_collection = Dict[UUID, Collection]  # list of collections
docs_in_cols = Dict[UUID, List[UUID]]  # mappping of documents to their collections
access_logs = Dict[UUID, List[Event]]  # mappping of documents to their access logs


@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}


@app.post("/collections/")
async def create_collection(
    file: UploadFile = File(...),
    user_id: UUID = None,
    share_state: SharedState = SharedState.private,
    token: str = Depends(oauth2_scheme),
    status_code=HTTPStatus.CREATED,
):
    verify_user(user_id, token)
    name = file.filename
    data = await file.read()
    collection = collections.create_collection(name, data, user_id)

    return {"message": "Collection created successfully", "uuid": collection.id}


@app.get("/collections/")
async def get_all_collections() -> List[Collection]:
    return collections.get_collections()


# TODO - add the ability to update a document collection
@app.put("/collections/{collection_uuid}")
async def update_collection(doc_uuid: UUID, file: UploadFile, user_id: UUID, token: str = Depends(oauth2_scheme)):
    verify_user(user_id, token)
    doc = collections.get_collection_by_id(doc_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.owner != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this document")
    update_collection(doc_uuid, file)


@app.delete("/collections/{collection_uuid}")
async def delete_collection(collection_uuid: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    verify_user(user_id, token)
    doc = collections.get_collection_by_id(collection_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if doc.owner != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
    delete_collection(collection_uuid)


# TODO - ability to delete a document
@app.delete("/collections/{collection_uuid}/{doc_uuid}")
async def delete_document(collection_uuid: UUID, doc_uuid: UUID, user_id: UUID, token: str = Depends(oauth2_scheme)):
    verify_user(user_id, token)
    doc = collections.get_collection_by_id(doc_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if doc.owner != user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
    pass


# TODO - ability to search for a document specifically
@app.get("/documents/search/{query}")
async def search_documents(query: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    verify_user(user_id, token)
    result = []
    for doc in documents_doi_sets.values():
        if query in doc.name or query in doc.doi:
            if (
                doc.access_control_list is None
                or (users["role"] == "admin" or users["username"] in doc.access_control_list)
                or doc.owner == users[user_id].username
            ):
                result.append(doc)
    return result


# TODO - ability to filter documents by type, size or owner
# filter documents by type, size or owner
@app.get("/documents/filter")
async def filter_documents(
    type: Optional[str] = None,
    size: Optional[int] = None,
    owner: Optional[str] = None,
    user_id: UUID = None,
    token: str = Depends(oauth2_scheme),
):
    verify_user(user_id, token)
    result = []
    for doc in documents_doi_sets.values():
        if (
            doc.access_control_list is None
            or (users["role"] == "admin" or users["username"] in doc.access_control_list)
            or doc.owner == users[user_id].username
        ):
            if type is not None and type != doc.type:
                continue
            if size is not None and size != doc.size:
                continue
            if owner is not None and owner != doc.owner:
                continue
            result.append(doc)
    return result


# TODO - get the history of a document
# get the history of a document
@app.get("/documents/history/{doi}")
async def get_document_history(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    verify_user(user_id, token)
    for doc in documents_doi_sets.values():
        if doc.doi == doi:
            if (
                doc.access_control_list is None
                or (users["role"] == "admin" or users["username"] in doc.access_control_list)
                or doc.owner == users[user_id].username
            ):
                if doc.access_from_data is not None and datetime.now() < doc.access_from_data:
                    raise HTTPException(status_code=403, detail="Document not accessible yet")
                return doc.history
    raise HTTPException(status_code=404, detail="Document not found")


# TODO - download a document
# download a document
@app.get("/documents/{doi}/download")
async def download_document(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    verify_user(user_id, token)
    for doc in documents_doi_sets.values():
        if doc.doi == doi:
            if (
                doc.access_control_list is None
                or (users["role"] == "admin" or users["username"] in doc.access_control_list)
                or doc.owner == users[user_id].username
            ):
                access_logs.append({"doi": doi, "access_date": datetime.now(), "user": users[user_id].username})
                if doc.access_from_data is not None and datetime.now() < doc.access_from_data:
                    raise HTTPException(status_code=403, detail="Document not accessible yet")
                doc.history.append("document downloaded by " + users[user_id].username + " on " + str(datetime.now()))
                return FileResponse(io.BytesIO(doc.content), filename=doc.name)
    raise HTTPException(status_code=404, detail="Document not found")


# TODO - get the access logs of a document
# get the access logs of a document
@app.get("/documents/{doi}/access_logs")
async def get_document_access_logs(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    verify_user(user_id, token)
    results = []
    if doi in sets_doi.keys():  # it is a set
        doc_set = documents_set[doi]
        if doc_set.owner == users[user_id].username or users["role"] == "admin":
            for log in access_logs:
                if log["doi"] == doi:
                    results.append(log)
            return results
    elif doi in documents_doi_sets.values():  # it is a document
        set_doi = documents_doi_sets[doi]
        doc_set = documents_set[set_doi]
        if doc_set.owner == users[user_id].username or users["role"] == "admin":
            for log in access_logs:
                if log["doi"] == doi:
                    results.append(log)
            return results
    raise HTTPException(status_code=404, detail="Document not found")


# register user
@app.post("/users/")
async def register_user(username: str, email: str, oauth_token: str):
    user = users.create_user(username, email, oauth_token)
    token = create_access_token(data={"sub": user.id})
    user.token = token
    users[user.id] = user
    return {"message": f"User {username} created successfully", "token": token}


# login user
@app.get("/users/")
async def login_user(username: str, oauth_token: str):
    user = users.get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.oauth_token != oauth_token:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.user_id})
    return {"access_token": access_token, "token_type": "bearer"}

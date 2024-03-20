import io
import uuid
from uuid import UUID
from datetime import datetime
from http.client import HTTPException
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.responses import FileResponse


from classes.commons import SharedState
from classes.document import Document, DocumentSet
from classes.event import Event, Create, Update, Delete, Share
from classes.user import User, UserRole

from security import oauth2_scheme, create_access_token, decode_token

app = FastAPI()

documents_collection = Dict[UUID, DocumentSet]  # list of DocumentSet (key is the set name)
docs_in_cols = Dict[UUID, List[UUID]]  # mappping of documents to their collections
access_logs = Dict[UUID, List[Event]]  # mappping of documents to their access logs
users: Dict[UUID, User] = {}  # list of dictionaries with the users (key is the user_id)


def raise_if_not_valid_user(user_id: UUID, token: str = Depends(oauth2_scheme)):
    if user_id not in users.keys():
        raise HTTPException(status_code=404, detail="User not found")
    this_user_token = users[user_id].token
    decoded_token = decode_token(token)
    if decoded_token != this_user_token:
        raise HTTPException(status_code=404, detail="Invalid user")


# root path
@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}


# create/upload a new document collection
@app.post("/documents/")
async def create_document(
    file: UploadFile = File(...),
    user_id: UUID = None,
    share_state: SharedState = SharedState.private,
    token: str = Depends(oauth2_scheme),
):
    raise_if_not_valid_user(user_id, token)
    date_time = datetime.now()
    set_name = str(user_id) + " " + str(date_time)
    content = await file.read()

    document = Document(name=file.filename, content=content)
    document.history.append(Create(user_id))

    document_set = DocumentSet(
        set_name=set_name,
        collection=[document],
        share_state=share_state,
        owner=user_id,
    )
    documents_collection[set_name] = document_set
    return {"message": "Document created successfully", "name": set_name}


# get documents_sets
# @app.get("/documents/")
# async def get_documents():
#     return documents_set


# get a document a document set or a document by its DOI
""" @app.get("/documents/{doi}")
async def get_document(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
    if doi in sets_doi.keys():  # it is a set
        doc_set = documents_set[doi]
        if (
            doc_set.access_control_list is None
            or (users["role"] == "admin" or users["username"] in doc_set.access_control_list)
            or doc_set.owner == users[user_id].username
        ):
            access_logs.append({"doi": doi, "access_date": datetime.now(), "user": users[user_id].username})
            if doc_set.access_from_data is not None and datetime.now() < doc_set.access_from_data:
                raise HTTPException(status_code=403, detail="Document not accessible yet")
            for doc in doc_set.collection:
                doc.history.append("set accessed by " + users[user_id].username + " on " + str(datetime.now()))
            return doc_set
    elif doi in documents_doi_sets.values():  # it is a document
        set_doi = documents_doi_sets[doi]
        doc_set = documents_set[set_doi]
        document = doc_set.collection[doi]
        if (
            document.access_control_list is None
            or (users["role"] == "admin" or users["username"] in document.access_control_list)
            or doc_set.owner == users[user_id].username
        ):
            access_logs.append({"doi": doi, "access_date": datetime.now(), "user": users[user_id].username})
            if document.access_from_data is not None and datetime.now() < document.access_from_data:
                raise HTTPException(status_code=403, detail="Document not accessible yet")
            document.history.append("document accessed by " + users[user_id].username + " on " + str(datetime.now()))
            return doc_set.collection[doi]
    raise HTTPException(status_code=404, detail="Document not found")
 """


# update a document collection
@app.put("/documents/{doc_uuid}")
async def update_document(doc_uuid: UUID, document: Document, user_id: UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
    if doc_uuid not in documents_collection.keys():
        raise HTTPException(status_code=404, detail="Document(s) not found")
    doc_set = documents_collection[doc_uuid]
    if doc_set.owner == users[user_id].username:
        collection = doc_set.collection
        for doc in collection:
            if doc.doi == document.doi:
                document.name = doc.name
                document.doc_id = doc.doc_id
                document.doi = doc.doc_id
                document.type = document.content_type
                document.size = document.size
                document.submission_date = doc.submission_date
                document.last_update = datetime.now()
                document.history = doc.history
                document.history.append("document updated by " + users[user_id].username + " on " + str(datetime.now()))
                collection.remove(doc)
                collection.append(document)
                doc_set.collection = collection
                return {"message": "Document updated successfully"}
    raise HTTPException(status_code=404, detail="Document(s) not found")


# delete a document or a document set
@app.delete("/documents/{doi}")
async def delete_document(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
    if doi in sets_doi.keys():  # it is a set
        doc_set = documents_set[doi]
    elif doi in documents_doi_sets.values():  # it is a document
        set_doi = documents_doi_sets[doi]
        doc_set = documents_set[set_doi]
    else:
        raise HTTPException(status_code=404, detail="Document(s) not found")
    if doc_set.owner == users[user_id].username:
        for doc in doc_set.collection:
            if doc.doi == doi:
                doc_set.collection.remove(doc)
                documents_doi_sets.pop(doi)
                return {"message": "Document deleted successfully"}
    raise HTTPException(status_code=404, detail="Document not found")


# search for a specific document
@app.get("/documents/search/{query}")
async def search_documents(query: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
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


# filter documents by type, size or owner
@app.get("/documents/filter")
async def filter_documents(
    type: Optional[str] = None,
    size: Optional[int] = None,
    owner: Optional[str] = None,
    user_id: UUID = None,
    token: str = Depends(oauth2_scheme),
):
    raise_if_not_valid_user(user_id, token)
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


# get the history of a document
@app.get("/documents/history/{doi}")
async def get_document_history(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
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


# download a document
@app.get("/documents/{doi}/download")
async def download_document(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
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


# get the access logs of a document
@app.get("/documents/{doi}/access_logs")
async def get_document_access_logs(doi: str, user_id: UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
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


# register users
@app.post("/users/")
async def register_user(username: str, email: str, mobile_key: str):
    user_id = uuid.uuid4()
    token = create_access_token(data={"sub": user_id})
    user = User(user_id=user_id, username=username, token=token, email=email, mobile_key=mobile_key)
    users[user_id] = user
    return {"message": "User registered successfully"}


# login users
@app.get("/users/")
async def login_user(username: str, mobile_key: str):
    for user in users:
        if user.username == username:
            if mobile_key == user.mobile_key:
                access_token = create_access_token(data={"sub": user.user_id})
                return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")

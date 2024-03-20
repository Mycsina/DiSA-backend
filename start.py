import base64
import hashlib
import io
import uuid
from datetime import datetime, timedelta, timezone
from http.client import HTTPException
from typing import Dict, List, Optional

import jwt
from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from classes import Document, DocumentSet, User, UserRole

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "ThIsIsAsEcReTkEy"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

documents_set = Dict[str, DocumentSet]  # list of DocumentSet (key is the set name)
sets_doi: List[str] = []  # list of DOIs of the sets
documents_doi_sets = Dict[
    str, str
]  # dictionary of DOIs of the documents and the DOI of the set they belong to (key is the set DOI)
access_logs = List[Dict[str, str]]  # list of dictionaries with the access logs of the documents
users: Dict[uuid.UUID, User] = {}  # list of dictionaries with the users (key is the user_id)


def raise_if_not_valid_user(user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
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


# create/upload a new document
@app.post("/documents/")
async def create_document(
    file: UploadFile = File(...),
    user_id: uuid.UUID = None,
    share_state: str = "private",
    access_control_list=None,
    token: str = Depends(oauth2_scheme),
):
    raise_if_not_valid_user(user_id, token)
    date_time = datetime.now()
    set_name = str(user_id) + str(date_time)
    content = await file.read()
    document_hash = hashlib.sha256(content).digest()
    doi = base64.urlsafe_b64encode(document_hash).decode("utf-8")
    document = Document(
        name=file.filename,
        content=content,
        doi=doi,
        type=file.content_type,
        size=file.size,
        submission_date=date_time,
        last_update=date_time,
        access_control_list=access_control_list,
        history=["created by " + users[user_id].username + " on " + str(date_time)],
    )
    if set_name in documents_set.keys():
        documents_doi_sets[documents_set[set_name].doi].append(doi)
        documents_set[set_name].collection.append(document)
        documents_set[set_name].num += 1
        documents_set[set_name].last_update = datetime.now()
    else:
        set_hash = hashlib.sha256(set_name).digest()
        set_doi = base64.urlsafe_b64encode(set_hash).decode("utf-8")
        documents_doi_sets[set_doi] = doi
        user_name = users[user_id].username
        document_set = DocumentSet(
            doi=set_doi,
            set_name=set_name,
            collection=[document],
            num=1,
            submission_date=datetime.now(),
            last_update=datetime.now(),
            share_state=share_state,
            owner=user_name,
            access_control_list=None,
            access_from_data=None,
        )
        documents_set[set_name] = document_set
        sets_doi.append(set_doi)
    return {"message": "Document created successfully", "doi": doi}


# get documents_sets
# @app.get("/documents/")
# async def get_documents():
#     return documents_set


# get a document a document set or a document by its DOI
@app.get("/documents/{doi}")
async def get_document(doi: str, user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
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


# update a document
@app.put("/documents/{doi}")
async def update_document(doi: str, document: Document, user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
    raise_if_not_valid_user(user_id, token)
    if doi in documents_doi_sets.values():  # it is a document
        set_doi = documents_doi_sets[doi]
    elif doi in sets_doi.keys():  # it is a set
        set_doi = doi
    else:
        raise HTTPException(status_code=404, detail="Document(s) not found")
    doc_set = documents_set[set_doi]
    if doc_set.owner == users[user_id].username:
        # delete the previous document with that doi and add the new one
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
async def delete_document(doi: str, user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
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
async def search_documents(query: str, user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
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
    user_id: uuid.UUID = None,
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
async def get_document_history(doi: str, user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
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
async def download_document(doi: str, user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
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
async def get_document_access_logs(doi: str, user_id: uuid.UUID, token: str = Depends(oauth2_scheme)):
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token
    except:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


# register users
@app.post("/users/register")
async def register_user(username: str, email: str, mobile_key: str, role: UserRole = UserRole.USER):
    user_id = uuid.uuid4()
    token = create_access_token(data={"sub": user_id})
    user = User(user_id=user_id, username=username, token=token, email=email, mobile_key=mobile_key, role=UserRole.USER)
    users[user_id] = user
    return {"message": "User registered successfully"}


# login users
@app.post("/users/login")
async def login_user(username: str, mobile_key: str):
    for user in users:
        if user.username == username:
            if mobile_key == user.mobile_key:
                access_token = create_access_token(data={"sub": user.user_id})
                return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")

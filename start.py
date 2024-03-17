import base64
import hashlib
from http.client import HTTPException
import io
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "ThIsIsAsEcReTkEy"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


class DocumentDoi(BaseModel):
    doi: str
    document_id: int

class Document(BaseModel):
    name: str
    content: bytes
    doi: DocumentDoi
    is_collection: Optional[bool] = False # indicates if the document is a collection of documents
    submission_date: Optional[datetime] = None
    last_update: Optional[datetime] = None # should be equal to submission_date if the document was never updated
    type: Optional[str] = None
    size: Optional[int] = None
    owner: Optional[str] = None
    access_control_list: Optional[List[str]] = None # list of users that have access to the document
    access_from_data: Optional[datetime] = None # date from which the document is accessible
    history: Optional[List[dict]] = None # list of dictionaries with the history of the document

class User(BaseModel):
    username: str
    email: str
    password: str
    role: str
    access_control_list: Optional[List[str]] = None # list of documents that the user has access to


documents = []
document_dois = []
access_logs = []
users = []

@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}

@app.post("/documents/")
async def create_document(document: Document):
    document_hash = hashlib.sha256(document.content).digest()
    doi = base64.urlsafe_b64encode(document_hash).decode('utf-8')
    if len(documents) > 0:
        document_id = documents[-1].document_id + 1
    else:
        document_id = 0
    document_doi = DocumentDoi(doi = doi, document_id = document_id)
    document.doi = document_doi
    document.submission_date = datetime.now()
    document.last_update = datetime.now()
    documents.append(document)
    document_dois.append(document_doi)
    return {"message": "Document created successfully", "doi": doi}

@app.get("/documents/")
async def get_documents():
    return documents

@app.get("/documents/{doi}")
async def get_document(doi: str, token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    for doc_doi in document_dois:
        if doc_doi.doi == doi:
            document = documents[doc_doi.document_id]
            if document.access_control_list is None or (users["role"] == "admin" or users["username"] in documents[doc_doi.document_id].access_control_list):
                access_logs.append({"doi": doi, "access_date": datetime.now()})
                return document
    raise HTTPException(status_code=404, detail="Document not found")

@app.put("/documents/{doi}")
async def update_document(doi: str, document: Document):
    for _, doc_doi in enumerate(document_dois):
        if doc_doi.doi == doi:
            documents[doc_doi.document_id] = document
            document.last_update = datetime.now()
            return {"message": "Document updated successfully"}
    raise HTTPException(status_code=404, detail="Document not found")

@app.delete("/documents/{doi}")
async def delete_document(doi: str):
    for _, doc_doi in enumerate(document_dois):
        if doc_doi.doi == doi:
            documents.pop(doc_doi.document_id)
            document_dois.pop(doc_doi.document_id)
            return {"message": "Document deleted successfully"}
    raise HTTPException(status_code=404, detail="Document not found")

@app.get("/documents/search/{query}")
async def search_documents(query: str):
    result = []
    for document in documents:
        if query in document.name or query in document.doi.doi:
            result.append(document)
    return result

@app.get("/documents/filter")
async def filter_documents(type: Optional[str] = None, size: Optional[int] = None, owner: Optional[str] = None):
    result = documents
    if type:
        result = [document for document in result if document.type == type]
    if size:
        result = [document for document in result if document.size == size]
    if owner:
        result = [document for document in result if document.owner == owner]
    return result

@app.get("/documents/history/{doi}")
async def get_document_history(doi: str):
    for _, doc_doi in enumerate(document_dois):
        if doc_doi.doi == doi:
            return documents[doc_doi.document_id].history
    raise HTTPException(status_code=404, detail="Document not found")

@app.get("/documents/{doi}/download")
async def download_document(doi: str):
    for doc_doi in document_dois:
        if doc_doi.doi == doi:
            document = documents[doc_doi.document_id]
            return FileResponse(io.BytesIO(document.content), filename=document.name)
    raise HTTPException(status_code=404, detail="Document not found")

@app.get("/documents/{doi}/access_logs")
async def get_document_access_logs(doi: str):
    result = []
    for log in access_logs:
        if log["doi"] == doi:
            result.append(log)
    return result






def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token
    except:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

@app.post("/users/register")
async def register_user(user: User):
    users.password = get_password_hash(user.password)
    users.append(user.dict())
    return {"message": "User registered successfully"}

@app.post("/users/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    for user in users:
        if user.username == form_data.username:
            if verify_password(form_data.password, user["password"]):
                access_token = create_access_token(data={"sub": user.username})
                return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")

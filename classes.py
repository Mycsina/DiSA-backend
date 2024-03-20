from enum import Enum
from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class SetDoi(BaseModel):
    doi: str
    set_id: int


class Document(BaseModel):
    name: str
    doc_id: uuid.UUID = uuid.uuid4()
    content: bytes
    doi: str
    type: str = None
    size: int = None
    submission_date: datetime = datetime.now()
    last_update: datetime = datetime.now()
    access_from_data: Optional[datetime] = None  # date from which the document is accessible
    history: List[str] = []  # list of dictionaries with the history of the document


SharedState = Enum("SharedState", "private public embargoed restricted")


class DocumentSet(BaseModel):
    doi: SetDoi
    set_id: uuid.UUID = uuid.uuid4()
    set_name: str
    collection: List[Document]
    num: int = 1
    submission_date: datetime = datetime.now()
    last_update: datetime = datetime.now()
    share_state: SharedState
    owner: str
    access_control_list: Optional[List[str]]  # list of users that have access to the document
    access_from_data: Optional[datetime]  # date from which the set is accessible


class User(BaseModel):
    user_id: uuid.UUID = uuid.uuid4()
    username: str
    token: str
    email: str
    mobile_key: str
    role: str

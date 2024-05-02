import uuid
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from classes.commons import SharedState
from classes.event import Event


class Document(BaseModel):
    name: str
    doc_id: UUID = uuid.uuid4()
    content: bytes
    size: int = None
    submission_date: datetime = datetime.now()
    last_update: datetime = datetime.now()
    access_from_data: Optional[datetime] = None  # date from which the document is accessible
    history: List[Event] = []  # list of events that happened to the document

    def __init__(self, name: str, content: bytes):
        self.name = name
        self.content = content
        self.size = len(content)


class DocumentSet(BaseModel):
    set_id: uuid.UUID = uuid.uuid4()
    name: str
    collection: List[Document]
    num: int = 1
    submission_date: datetime = datetime.now()
    last_update: datetime = datetime.now()
    share_state: SharedState
    owner: uuid.UUID
    access_control_list: Optional[List[uuid.UUID]] = None  # list of users that have access to the document
    access_from_date: Optional[datetime] = None  # date from which the set is accessible

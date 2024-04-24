import math
import uuid
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from classes.commons import SharedState
from classes.event import Event, Create


class Document(BaseModel):
    name: str
    doc_id: UUID = uuid.uuid4()
    content: bytes
    size: int = None
    last_update: datetime = datetime.now()
    history: List[Event] = []  # list of events that happened to the document

    def __init__(self, name: str, content: bytes):
        self.name = name
        self.content = content
        self.size = len(content)
        self.history.append(Create())


class Directory(BaseModel):
    """
    Describes a directory and its contents
    """

    name: str
    parent: Optional["Directory"] = None
    children: List[Union[Document, "Directory"]] = []
    owner: uuid.UUID

    def __init__(self, name: str, parent: Optional["Directory"] = None):
        self.name = name
        self.parent = parent

    @property
    def last_update(self):
        latest_update = math.inf
        for child in self.children:
            if child.last_update < latest_update:
                latest_update = child.last_update

    @property
    def size(self):
        size = 0
        for child in self.children:
            size += child.size
        return size


class Collection(BaseModel):
    id: uuid.UUID = uuid.uuid4()
    name: str
    structure: Directory
    submission_date: datetime = datetime.now()
    share_state: SharedState
    owner: uuid.UUID
    access_control_list: Optional[List[uuid.UUID]] = None  # list of users that have access to this collection
    access_from_date: Optional[datetime] = None  # date from which the collection is accessible

    def __init__(self, name: str, owner: uuid.UUID, files: List[Document]):
        self.name = name
        self.owner = owner
        self.structure = Directory(name)
        for file in files:
            self.structure.contents.append(file)

    @property
    def last_update(self):
        return self.structure.last_update

    @property
    def size(self):
        return self.structure.size

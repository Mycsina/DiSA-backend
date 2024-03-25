from ast import Delete
import math
import uuid
from datetime import datetime
from typing import Any, Generator, List, Optional, Tuple, Union
from uuid import UUID

from sqlmodel import Field, ForeignKey, SQLModel
from pydantic import BaseModel

from classes.event import Access, Event, Create, Update

from enum import Enum


class SharedState(str, Enum):
    private = "private"
    public = "public"
    embargoed = "embargoed"
    restricted = "restricted"


# class Document(BaseModel):
    # name: str
    # doc_id: UUID = uuid.uuid4()
    # content: bytes
    # size: int = None
    # last_update: datetime = datetime.now()
    # history: List[Event] = []  # list of events that happened to the document

    # def __init__(self, name: str, content: bytes):
    #     self.name = name
    #     self.content = content
    #     self.size = len(content)
    #     self.history.append(Create())
class Document(SQLModel, table=True):
    id: uuid.UUID = Field(index=True, default_factory=uuid.uuid4, primary_key=True)
    folder: uuid.UUID = Field(index=True, nullable=False, ForeignKey="folder.id")
    name: str = Field(nullable=False)
    content: bytes = Field(nullable=False)
    size: int = Field(nullable=False)
    submission_date: datetime = Field(default_factory=datetime.now, nullable=False)
    last_updated: Optional[datetime] = Field(default=None)
    access_from_date: Optional[datetime] = Field(default=None)
    history: List[Event] = Field(default_factory=list)

    def __init__(self, name: str, content: bytes):
        super().__init__(name=name, content=content)
        self.size = len(content)
        self.history.append(Create(user=uuid.uuid4(), doc=self.id))

    def access(self, user: UUID):
        self.history.append(Access(user=user, doc=self.id))

    def update(self, user:UUID, new_content: bytes):
        self.content = new_content
        self.size = len(new_content)
        self.last_updated = datetime.now()
        self.history.append(Update(user=user, doc=self.id))

    def delete(self, user: UUID):
        self.history.append(Delete(user=user, doc=self.id))


# class Directory(BaseModel):
#     """
#     Describes a directory and its contents
#     """

#     name: str
#     parent: Optional["Directory"] = None
#     children: List[Union[Document, "Directory"]] = []
#     owner: uuid.UUID

#     def __init__(self, name: str, parent: Optional["Directory"] = None):
#         self.name = name
#         self.parent = parent

#     @property
#     def last_update(self):
#         latest_update = math.inf
#         for child in self.children:
#             if child.last_update < latest_update:
#                 latest_update = child.last_update

#     @property
#     def size(self):
#         size = 0
#         for child in self.children:
#             size += child.size
#         return size

#     def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
#         for item in self.children:
#             if item is Document:
#                 yield Document
class Directory(SQLModel, table=True):
    """
    Describes a directory and its contents
    """
    id: uuid.UUID = Field(index=True, default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    parent: Optional[uuid.UUID] = Field(default=None, ForeignKey="folder.id")
    owner: uuid.UUID = Field(nullable=False)
    children: List[Union[Document, "Directory"]] = Field(default_factory=list)

    def __init__(self, name: str, parent: Optional["Directory"] = None):
        super().__init__(name=name, parent=parent)

    @property
    def last_update(self):
        latest_update = datetime.min
        for child in self.children:
            if child.last_updated > latest_update:
                latest_update = child.last_updated
        return latest_update
    
    @property
    def size(self):
        size = 0
        for child in self.children:
            size += child.size
        return size
    
    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        for item in self.children:
            if item is Document:
                yield Document


# class Collection(BaseModel):
#     id: uuid.UUID = uuid.uuid4()
#     name: str
#     structure: Directory
#     submission_date: datetime = datetime.now()
#     share_state: SharedState
#     owner: uuid.UUID
#     access_control_list: Optional[List[uuid.UUID]] = None  # list of users that have access to this collection
#     access_from_date: Optional[datetime] = None  # date from which the collection is accessible

#     def __init__(self, name: str, owner: uuid.UUID, files: List[Document]):
#         self.name = name
#         self.owner = owner
#         self.structure = Directory(name)
#         for file in files:
#             self.structure.contents.append(file)

#     @property
#     def last_update(self):
#         return self.structure.last_update

#     @property
#     def size(self):
#         return self.structure.size

#     def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
#         for item in self.structure:
#             yield item
#         # self.structure.__iter__()
class Collection(SQLModel, table=True):
    id: uuid.UUID = Field(index=True, default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    owner: uuid.UUID = Field(index=True, nullable=False, ForeignKey="user.id")
    submission_date: datetime = Field(default_factory=datetime.now, nullable=False)
    last_update: Optional[datetime] = Field(default=None)
    share_state: SharedState = Field(default=SharedState.private, nullable=False)
    access_from_date: Optional[datetime] = Field(default=None)
    structure: Directory = Field(nullable=False)
    access_control_list: Optional[List[uuid.UUID]] = Field(default=None)
    
    def __init__(self, name: str, owner: uuid.UUID, files: List[Document]):
        super().__init__(name=name, owner=owner)
        self.structure = Directory(name)
        for file in files:
            self.structure.children.append(file)
    
    @property
    def last_update(self):
        return self.structure.last_update
    
    @property
    def size(self):
        return self.structure.size
    
    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        for item in self.structure:
            yield item

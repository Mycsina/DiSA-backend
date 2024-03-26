from datetime import datetime
from enum import Enum
from typing import Any, Generator, List, Tuple
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from models.event import Event
from models.folder import Folder


class SharedState(str, Enum):
    private = "private"
    public = "public"
    embargoed = "embargoed"
    restricted = "restricted"


class DocumentBase(SQLModel):
    name: str
    size: int
    submission_date: datetime
    last_updated: datetime | None = None
    access_from_date: datetime | None = None


class Document(DocumentBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    folder: UUID = Field(index=True, foreign_key="folder.id")
    submission_date: datetime = Field(default_factory=datetime.now)


class DocumentIntake(DocumentBase):
    content: bytes
    history: list[Event] = []


class CollectionBase(SQLModel):
    id: UUID
    name: str
    owner: UUID
    submission_date: datetime
    last_update: datetime | None
    share_state: SharedState = SharedState.private
    access_from_date: datetime | None

    def __init__(self, name: str, owner: UUID, files: List[Document]):
        super().__init__(name=name, owner=owner)
        self.structure = Folder(name)
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


class CollectionIntake(CollectionBase):
    structure: Folder
    access_control_list: List[UUID] | None


class Collection(CollectionBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    root: UUID = Field(foreign_key="folder.id")

    # folder: "Folder" = Relationship(back_populates="folder")

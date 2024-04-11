from datetime import datetime
from enum import Enum
from typing import Any, Generator, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from models.event import CollectionEvent, DocumentEvent
from models.folder import Folder, FolderIntake
from models.update import Update
from models.user import User


class SharedState(str, Enum):
    private = "private"
    public = "public"
    embargoed = "embargoed"
    restricted = "restricted"


class DocumentBase(SQLModel):
    name: str
    size: int
    access_from_date: datetime | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Document(DocumentBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    folder_id: UUID = Field(index=True, foreign_key="folder.id")
    collection_id: UUID = Field(index=True, foreign_key="collection.id")

    events: list["DocumentEvent"] = Relationship(back_populates="document")
    folder: Folder = Relationship(back_populates="documents")
    collection: "Collection" = Relationship(back_populates="documents")
    previous: Optional["Update"] = Relationship(
        back_populates="new", sa_relationship_kwargs={"foreign_keys": "Update.updated_id"}
    )
    next: Optional["Update"] = Relationship(
        back_populates="old", sa_relationship_kwargs={"foreign_keys": "Update.previous_id"}
    )


class DocumentIntake(DocumentBase):
    content: bytes
    parent_folder: FolderIntake


class CollectionBase(SQLModel):
    id: UUID
    name: str
    owner_id: UUID
    share_state: SharedState = SharedState.private
    access_from_date: datetime | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
    owner_id: UUID | None = Field(default=None, foreign_key="user.id", nullable=False)

    folder: Folder = Relationship(back_populates="collection")
    owner: "User" = Relationship(back_populates="collections")
    documents: list["Document"] = Relationship(back_populates="collection")
    events: list["CollectionEvent"] = Relationship(back_populates="collection")

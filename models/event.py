from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.collection import Document, Collection

from models.user import User


class EventTypes(str, Enum):
    Access = "access"
    Create = "create"
    Delete = "delete"


class EventBase(SQLModel):
    timestamp: datetime = datetime.now()
    type: EventTypes

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timestamp = datetime.now()


class EventIntake(EventBase):
    user: User


class DocumentEvent(EventBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    document_id: UUID = Field(foreign_key="document.id")
    type: EventTypes = Field(default=EventTypes.Access)

    user: User = Relationship(back_populates="events")
    document: "Document" = Relationship(back_populates="events")


class CollectionEvent(EventBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    collection_id: UUID = Field(foreign_key="collection.id")
    type: EventTypes = Field(default=EventTypes.Access)

    user: User = Relationship(back_populates="events")
    collection: "Collection" = Relationship(back_populates="events")

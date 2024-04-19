from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel
from datetime import datetime
from uuid import UUID, uuid4

from models.user import User

if TYPE_CHECKING:
    from models.collection import Document


class Update(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: UUID = Field(foreign_key="user.id")
    previous_id: UUID = Field(foreign_key="document.id")
    updated_id: UUID = Field(foreign_key="document.id")

    user: User = Relationship(back_populates="updates")
    old: "Document" = Relationship(
        back_populates="previous", sa_relationship_kwargs={"foreign_keys": "Update.previous_id"}
    )
    new: "Document" = Relationship(back_populates="next", sa_relationship_kwargs={"foreign_keys": "Update.updated_id"})

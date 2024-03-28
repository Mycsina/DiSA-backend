from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.collection import Collection, Document

from models.user import User


class FolderBase(SQLModel):
    name: str
    owner: User
    parent: Optional["FolderBase"]


class FolderIntake(FolderBase):
    children: list[Union["Document", "FolderIntake"]] = []


class Folder(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    owner_id: UUID = Field(foreign_key="user.id")
    parent_id: UUID | None = Field(default=None, foreign_key="folder.id")

    parent: Optional["Folder"] = Relationship(
        back_populates="sub_folders", sa_relationship_kwargs=dict(remote_side="Folder.id")
    )
    sub_folders: list["Folder"] = Relationship(back_populates="parent")

    documents: list["Document"] = Relationship(back_populates="folder")
    owner: User = Relationship(back_populates="folders")
    collection: "Collection" = Relationship(back_populates="folders")

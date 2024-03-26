from typing import TYPE_CHECKING, List, Union, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    from models.collection import Document

from models.user import User


class FolderBase(SQLModel):
    name: str
    owner: User
    parent: Optional["FolderBase"]


class FolderIntake(FolderBase):
    children: List[Union["Document", "FolderIntake"]] = []


class Folder(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    owner_id: UUID = Field(foreign_key="user.id")
    parent_id: UUID | None = Field(default=None, foreign_key="folder.id")

    # parent: Optional["Folder"] = Relationship(
    #    back_populates="children", sa_relationship_kwargs=dict(remote_side="Folder.id")
    # )
    # children: list["Folder"] = Relationship(back_populates="parent")

    # TODO - make documents aware of their parent folder
    # TODO - make the relationships bidirectional so we get nice sweet ORM magic

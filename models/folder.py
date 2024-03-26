from datetime import datetime
from typing import TYPE_CHECKING, Any, Generator, List, Tuple, Union, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.document import Document

from models.user import User


class FolderBase(SQLModel):
    name: str
    owner: User
    parent: Optional["FolderBase"]


class FolderIntake(SQLModel):
    children: List[Union["Document", "FolderIntake"]]

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
                yield item


class Folder(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    parent_id: UUID | None = Field(default=None, foreign_key="folder.id")

    parent: Optional["Folder"] = Relationship(
        back_populates="children", sa_relationship_kwargs=dict(remote_side="Folder.id")
    )
    children: list["Folder"] = Relationship(back_populates="parent")

    # TODO - make documents aware of their parent folder
    # TODO - make the relationships bidirectional so we get nice sweet ORM magic

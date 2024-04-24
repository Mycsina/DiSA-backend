from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.collection import Collection, Document, DocumentIntake


class FolderBase(SQLModel):
    name: str
    parent: Optional["FolderBase"] = None


class FolderIntake(FolderBase):
    children: list[Union["DocumentIntake", "FolderIntake"]] = []

    def __str__(self):
        """Return tabulated string representation of the folder structure."""
        return "\n".join(self.tree())

    def tree(self, prefix: str = ""):
        # https://stackoverflow.com/questions/9727673/list-directory-tree-structure-in-python
        """A recursive generator, given a directory Path object
        will yield a visual tree structure line by line
        with each line prefixed by the same characters
        """
        # prefix components:
        space = "    "
        branch = "│   "
        # pointers:
        tee = "├── "
        last = "└── "

        contents = self.children
        # contents each get pointers that are ├── with a final └── :
        if prefix == "":
            yield self.name
        pointers = [tee] * (len(contents) - 1) + [last]
        for pointer, path in zip(pointers, contents):
            yield prefix + pointer + path.name
            if isinstance(path, FolderIntake):  # extend the prefix and recurse:
                extension = branch if pointer == tee else space
                # i.e. space because last, └── , above so no more |
                yield from path.tree(prefix + extension)


class FolderOut(FolderBase):
    children: list[Union["Document", "FolderOut"]] = []


class Folder(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    collection_id: UUID | None = Field(default=None, foreign_key="collection.id", nullable=False)
    parent_id: UUID | None = Field(default=None, foreign_key="folder.id")

    parent: Optional["Folder"] = Relationship(
        back_populates="sub_folders", sa_relationship_kwargs=dict(remote_side="Folder.id")
    )
    sub_folders: list["Folder"] = Relationship(back_populates="parent")

    documents: list["Document"] = Relationship(back_populates="folder")
    collection: "Collection" = Relationship(back_populates="folder")

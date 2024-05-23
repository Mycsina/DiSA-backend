from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.collection import Collection, Document
    from models.user import User


class DocumentPaperless(SQLModel, table=True):
    """
    A document is represented by a document in Paperless-ngx.
    """

    paperless_id: int = Field(primary_key=True)
    doc_id: UUID | None = Field(default=None, index=True, foreign_key="document.id")

    document: "Document" = Relationship(back_populates="paperless")


class CollectionPaperless(SQLModel, table=True):
    """
    A collection is represented by a tag in Paperless-ngx.
    """

    paperless_id: int = Field(primary_key=True)
    collection_id: UUID | None = Field(default=None, index=True, foreign_key="collection.id")

    collection: "Collection" = Relationship(back_populates="paperless")


class UserPaperless(SQLModel, table=True):
    """
    A user is represented by a correspondent in Paperless-ngx.
    """

    paperless_id: int = Field(primary_key=True)
    user_id: UUID | None = Field(default=None, index=True, foreign_key="user.id")

    user: "User" = Relationship(back_populates="paperless")

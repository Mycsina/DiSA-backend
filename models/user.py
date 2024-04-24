from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.collection import Collection
    from models.event import CollectionEvent, DocumentEvent
    from models.update import Update
    from models.paperless import UserPaperless


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserSafe(SQLModel):
    name: str | None = None
    email: str
    role: UserRole | None = UserRole.USER


class UserBase(SQLModel):
    name: str | None = None
    email: str
    nic: str
    password: str | None = None
    cmd_token: str | None = None
    token: str | None = None
    role: UserRole | None = UserRole.USER


class UserCreate(UserBase):
    name: str
    email: str
    password: str
    nic: str


class UserCMDCreate(UserBase):
    email: str
    cmd_token: str


class User(UserBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True)
    nic: str = Field(unique=True)
    role: UserRole = Field(default=UserRole.USER)

    doc_events: list["DocumentEvent"] = Relationship(back_populates="user")
    col_events: list["CollectionEvent"] = Relationship(back_populates="user")
    collections: list["Collection"] = Relationship(back_populates="owner")
    updates: list["Update"] = Relationship(back_populates="user")
    paperless: Optional["UserPaperless"] = Relationship(back_populates="user")


def strip_sensitive(user: UserBase) -> UserSafe:
    return UserSafe(email=user.email, role=user.role, name=user.name)

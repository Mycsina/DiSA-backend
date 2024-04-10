from enum import Enum
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.event import Event
    from models.collection import Collection
    from models.update import Update


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
    password: str | None = None
    mobile_key: str | None = None
    token: str | None = None
    role: UserRole | None = UserRole.USER


class UserCreate(UserBase):
    name: str
    email: str
    password: str


class UserCMDCreate(UserBase):
    email: str
    mobile_key: str
    session_token: str


class User(UserBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True)
    role: UserRole = Field(default=UserRole.USER)

    events: list["Event"] = Relationship(back_populates="user")
    collections: list["Collection"] = Relationship(back_populates="owner")
    updates: list["Update"] = Relationship(back_populates="user")


def strip_sensitive(user: User) -> UserSafe:
    return UserSafe(email=user.email, role=user.role, name=user.name)
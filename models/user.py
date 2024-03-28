from enum import Enum
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.event import Event
    from models.folder import Folder


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


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
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True)
    role: UserRole = Field(default=UserRole.USER)

    events: list["Event"] = Relationship(back_populates="user")
    folders: list["Folder"] = Relationship(back_populates="owner")

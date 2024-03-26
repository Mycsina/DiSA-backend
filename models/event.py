from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from models.user import User


class EventTypes(str, Enum):
    Access = "access"
    Create = "create"
    Update = "update"
    Delete = "delete"


class EventBase(SQLModel):
    timestamp: datetime
    type: EventTypes


class EventIntake(EventBase):
    user: User


class Event(EventBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")

    user: User | None = Relationship(back_populates="events")

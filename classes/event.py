from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


# class Event(BaseModel):
#     user_id: UUID
#     timestamp: datetime = datetime.now()

#     def __init__(self, user_id: UUID):
#         self.user_id = user_id
class Event(SQLModel, table=True):
    id: UUID = Field(index=True, default_factory=UUID.uuid4, primary_key=True)
    user: UUID = Field(nullable=False, ForeignKey="user.id")
    timestamp: datetime = Field(default_factory=datetime.now, nullable=False)
    doc: Optional[str] = Field(default=None, ForeignKey="document.id")
    type: Optional[str] = Field(default=None)

    def __init__(self, user: UUID):
        super().__init__(user=user)


class Access(Event):
    pass


class Create(Event):
    pass


class Update(Event):
    pass


class Delete(Event):
    pass

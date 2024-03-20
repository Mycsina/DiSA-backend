from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Event(BaseModel):
    user_id: UUID
    timestamp: datetime = datetime.now()

    def __init__(self, user_id: UUID):
        self.user_id = user_id


class Access(Event):
    pass


class Create(Event):
    pass


class Update(Event):
    pass


class Delete(Event):
    pass

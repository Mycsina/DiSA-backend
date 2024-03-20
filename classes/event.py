from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel


class EventTypes(str, Enum):
    ACCESS = "access"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class Event(BaseModel):
    user_id: UUID
    timestamp: datetime = datetime.now()
    type: EventTypes

    def __init__(self, user_id: UUID):
        self.user_id = user_id


class AccessEvent(Event):
    type = EventTypes.ACCESS


class CreateEvent(Event):
    type = EventTypes.CREATE


class UpdateEvent(Event):
    type = EventTypes.UPDATE


class DeleteEvent(Event):
    type = EventTypes.DELETE

from enum import Enum

from pydantic import BaseModel


class SetDoi(BaseModel):
    doi: str
    set_id: int


class SharedState(str, Enum):
    private = "private"
    public = "public"
    embargoed = "embargoed"
    restricted = "restricted"

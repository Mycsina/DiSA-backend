from enum import Enum


class SharedState(str, Enum):
    private = "private"
    public = "public"
    embargoed = "embargoed"
    restricted = "restricted"

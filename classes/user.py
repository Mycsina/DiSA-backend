from enum import Enum
from typing import Optional
import uuid
from uuid import UUID

from pydantic import BaseModel


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    id: UUID = uuid.uuid4()
    name: str
    token: str
    email: str
    mobile_key: str
    role: UserRole = UserRole.USER

    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email

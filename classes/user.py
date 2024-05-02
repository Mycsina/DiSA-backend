from enum import Enum
import uuid
from uuid import UUID

from pydantic import BaseModel


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    user_id: UUID = uuid.uuid4()
    username: str
    token: str
    email: str
    role: UserRole = UserRole.USER

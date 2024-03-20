from enum import Enum
import uuid
from uuid import UUID

from pydantic import BaseModel


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    id: UUID = uuid.uuid4()
    username: str
    email: str
    oauth_token: str
    token: str
    role: UserRole = UserRole.USER

    def __init__(self, username: str, email: str, oauth_token: str):
        self.username = username
        self.email = email
        self.oauth_token = oauth_token

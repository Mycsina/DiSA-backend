from typing import List, Optional
from uuid import UUID

from classes.user import User

USERS: List[User] = []


def add_user(user: User):
    USERS.append(user)


def create_user(username: str, email: str, oauth_token: str) -> User:
    user = User(username, email, oauth_token)
    add_user(user)
    return user


def get_user_by_id(user_id: UUID) -> Optional[User]:
    for user in USERS:
        if user.id == user_id:
            return user
    return None


def get_user_by_username(username: str) -> Optional[User]:
    for user in USERS:
        if user.username == username:
            return user
    return None

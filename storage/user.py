from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
import storage.models as models
from classes.user import User


def create_user(db: Session, user: User) -> models.User:
    db_user = models.User(
        username=user.username,
        email=user.email,
        password=user.password,
        id_token=user.id_token,
        token=user.token,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: UUID) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

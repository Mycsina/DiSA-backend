from typing import Optional
from uuid import UUID

from sqlmodel import Session
from models import User as DBUser
from classes.user import User


def create_user(db: Session, user: User) -> DBUser:
    db_user = DBUser(
        name=user.name,
        email=user.email,
        token=user.token,
        email=user.email,
        mobile_key=user.mobile_key,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: UUID) -> Optional[DBUser]:
    return db.query(DBUser).filter(DBUser.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[DBUser]:
    return db.query(DBUser).filter(DBUser.username == username).first()

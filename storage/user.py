from uuid import UUID

from sqlmodel import Session, select

from models.user import User, UserCreate, UserCMDCreate


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        name=user.name,
        email=user.email,
        password=user.password,
    )
    db.add(db_user)
    db.commit()
    return db_user


def create_cmd_user(db: Session, user: UserCMDCreate) -> User:
    db_user = User(
        email=user.email,
        mobile_key=user.mobile_key,
    )
    db.add(db_user)
    db.commit()
    return db_user


def update_user_token(db: Session, user: User, token: str) -> User:
    user.token = token
    print(user)
    db.add(user)
    db.commit()
    return user


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    statement = select(User).where(User.id == user_id)
    results = db.exec(statement)
    return results.first()


def get_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.name == username)
    results = db.exec(statement)
    return results.first()

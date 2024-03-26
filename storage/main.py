from typing import TypeVar

from sqlmodel import Session, SQLModel, create_engine

T = TypeVar("T")


sqlite_file_name = "database.db"
DB_URL = f"sqlite:///storage/{sqlite_file_name}"

TEMP_FOLDER = "tmp"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def acquire_db():
    return Session(engine)


def add_and_refresh(db: Session, obj: T) -> T:
    """Add an object to the database and refresh it to get the generated defaults."""
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

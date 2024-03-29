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

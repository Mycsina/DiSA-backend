import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

TEST = True if os.getenv("TEST") else False

TEMP_FOLDER = os.getenv("TEMP_FOLDER")
if TEMP_FOLDER is None:
    TEMP_FOLDER = "tmp"

if TEST:
    sqlite_file_name = "test.db"
    DB_URL = f"sqlite:///test/{sqlite_file_name}"
else:
    sqlite_file_name = "database.db"
    DB_URL = f"sqlite:///storage/{sqlite_file_name}"


engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def acquire_db():
    return Session(engine)

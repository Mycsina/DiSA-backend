import os

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine
from sam_client import SAMClient

load_dotenv(override=True)


def must_getenv(var_name: str, strict: bool = False) -> str | None:
    value = os.getenv(var_name)
    if value is None and strict is True:
        raise ValueError(f"{var_name} must be set in the environment")
    return value


# Archivematica and Storage Service variables
AM_TRANSFER_PATH = must_getenv("AM_TRANSFER_PATH")
AM_URL = must_getenv("AM_URL")
AM_USER = must_getenv("AM_USER")
AM_API_KEY = must_getenv("AM_API_KEY")
SS_USER = must_getenv("SS_USER")
SS_API_KEY = must_getenv("SS_API_KEY")

TEMP_FOLDER = must_getenv("TEMP_FOLDER", True)
tmp = os.getenv("TEST_MODE")
TEST_MODE = False
if tmp is not None:
    if tmp != 0:
        TEST_MODE = True

if TEST_MODE:
    sqlite_file_name = "test.db"
    DB_URL = f"sqlite:///test/{sqlite_file_name}"
else:
    sqlite_file_name = "database.db"
    DB_URL = f"sqlite:///storage/{sqlite_file_name}"


engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


sam = SAMClient(am_url=AM_URL)
sam.setup_login(AM_USER, AM_API_KEY)
sam.ss_setup_login(SS_USER, SS_API_KEY)


def create_am_package(
    tranfer_directory: str,
    transfer_name: str | None = None,
    transfer_type: str = "standard",
    pipeline: str = "automated",
) -> str:
    return sam.create_package(tranfer_directory, transfer_name, transfer_type, pipeline)["id"]

import logging
import os

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

from models.collection import Collection, Document
from models.user import User

load_dotenv(override=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def must_getenv(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        logger.error(f"{var_name} must be set in the environment")
        raise ValueError(f"{var_name} must be set in the environment")
    return value


TEMP_FOLDER = must_getenv("TEMP_FOLDER")
logger.debug(f"TEMP_FOLDER set to: {TEMP_FOLDER}")

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

logger.debug(f"Using DB_URL: {DB_URL}")


STORAGE = must_getenv("STORAGE")
logger.debug(f"STORAGE set to: {STORAGE}")


class StorageStrategy:
    def upload_folder(self, db: Session, mappings: dict, collection: Collection, user: User):
        raise NotImplementedError

    def create_collection(self, db: Session, collection: Collection, name: str):
        raise NotImplementedError

    def create_user(self, db: Session, user: User, name: str):
        raise NotImplementedError

    def create_document(self, db: Session, document: Document, name: str):
        raise NotImplementedError

    @staticmethod
    def verify_matches_interface(obj):
        return (
            hasattr(obj, "create_collection")
            and hasattr(obj, "create_user")
            and hasattr(obj, "create_document")
            and hasattr(obj, "upload_folder")
        )


match STORAGE:
    case "paperless":
        PAPERLESS_URL = must_getenv("PAPERLESS_URL")
        PAPERLESS_TOKEN = must_getenv("PAPERLESS_TOKEN")

        logger.debug(f"PAPERLESS_URL: {PAPERLESS_URL}")
        logger.debug(f"PAPERLESS_TOKEN set: {PAPERLESS_TOKEN}")

        import storage.adapters.paperless as ppl

        store = ppl
    case _:
        raise ValueError("Invalid STORAGE value. Please use one of the following: 'paperless'.")


if not StorageStrategy.verify_matches_interface(store):
    raise ValueError("Storage strategy does not match the required interface. This should never happen.")


engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    logger.info("Database and tables created successfully.")

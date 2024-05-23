import logging
import os

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine

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

PAPERLESS_URL = must_getenv("PAPERLESS_URL")
logger.debug(f"PAPERLESS_URL: {PAPERLESS_URL}")
PAPERLESS_TOKEN = must_getenv("PAPERLESS_TOKEN")
logger.debug(f"PAPERLESS_TOKEN set: {PAPERLESS_TOKEN}")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    logger.info("Database and tables created successfully.")

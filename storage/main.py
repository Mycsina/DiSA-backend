from sqlmodel import SQLModel, create_engine

sqlite_file_name = "database.db"
DB_URL = f"sqlite:///storage/{sqlite_file_name}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

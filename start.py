import os
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

import routes.collections
import routes.documents
import routes.users
from storage.main import DB_URL, TEMP_FOLDER, TEST_MODE, engine
import routes


def on_startup():
    if TEST_MODE:
        db_path = DB_URL.split("///")[1]
        shutil.copy2(db_path, db_path + ".bak")
    SQLModel.metadata.create_all(engine)
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)


def on_shutdown():
    if TEST_MODE:
        db_path = DB_URL.split("///")[1]
        shutil.copy2(db_path + ".bak", db_path)
        os.remove(db_path + ".bak")
    if os.path.exists(TEMP_FOLDER):
        # Remove the temporary folder and its contents
        shutil.rmtree(TEMP_FOLDER)


@asynccontextmanager
async def lifespan(app: FastAPI):
    on_startup()
    yield
    on_shutdown()


app = FastAPI(lifespan=lifespan)

# TODO: Make this dev only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Tighten database constraints


@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}


app.include_router(routes.users.users_router)
app.include_router(routes.collections.collections_router)
app.include_router(routes.documents.documents_router)

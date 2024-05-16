import os
import shutil
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session

import routes.collections
import routes.documents
import routes.users
from models.user import User
from storage.main import DB_URL, TEMP_FOLDER, TEST_MODE, engine
from utils.security import get_current_user
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

# Logging middleware for every request and response
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_request(request, call_next):
    logger.info(f"Received request: {request.method} {request.url}")
    response = await call_next(request)
    return response

@app.middleware("http")
async def log_response(request, call_next):
    response = await call_next(request)
    logger.info(f"Sent response: {response.status_code}")
    return response

@app.get("/")
async def root():
    return {"message": "Welcome to DiSA"}


@app.get("/ping")
async def ping(user: Annotated[User, Depends(get_current_user)]):
    with Session(engine) as session:
        return "pong"


app.include_router(routes.users.users_router)
app.include_router(routes.collections.collections_router)
app.include_router(routes.documents.documents_router)

import logging
from datetime import datetime
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse
from sqlmodel import Session

import storage.collection as collections
import storage.user as users
from models.collection import (
    Collection,
    CollectionInfo,
    CollectionPermissionInfo,
    Permission,
)
from models.folder import FolderIntake
from models.user import User
from storage.main import engine
from utils.security import get_current_user, get_optional_user

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

collections_router = APIRouter(
    prefix="/collections",
    tags=["collections"],
)

# Create a new collection
@collections_router.post("/")
async def create_collection(
    user: Annotated[User, Depends(get_current_user)],
    transaction_address: Annotated[str, Form()],
    file: UploadFile = File(...),
):
    with Session(engine) as session:
        name = file.filename
        if name is None:
            raise HTTPException(status_code=400, detail="No file name provided")
        data = await file.read()
        collection = await collections.create_collection(session, name, data, user, transaction_address)
        logger.info(f"Collection created sucessfully: {collection.id}")
        return {"message": "Collection created successfully", "uuid": collection.id}


# TODO: test this
@collections_router.get("/download")
async def download_collection(
    user: Annotated[User | None, Depends(get_optional_user)],
    col_uuid: UUID,
    email: str | None = None,
) -> FileResponse:
    # Verify user or email is provided
    if user is None and email is None:
        logger.error("No authentication method provided.")
        raise HTTPException(status_code=400, detail="No authentication method provided")
    if user is not None and email is not None:
        logger.error("Two authentication methods provided when only one is allowed.")
        raise HTTPException(status_code=400, detail="Provide only one authentication method")
    with Session(engine) as session:
        db_user = user
        # If email is provided, get the anonymous user
        if email is not None:
            db_user = users.get_user_by_email(session, email)
        if db_user is None:
            logger.error("Anonymous user not found. Likely this email does not have permission.")
            raise HTTPException(
                status_code=404, detail="Anonymous user not found. Does this email have permission?")
        col = collections.get_collection_by_id(session, col_uuid, db_user)
        if col is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_read(db_user):
            raise HTTPException(
                status_code=403, detail="You do not have permission to access this collection")
        file_path = await collections.download_collection(session, col, db_user)
        return FileResponse(
            file_path,
            filename=col.name,
        )

# TODO - make sure it is necessary (maybe for admin purposes only)
@collections_router.get("/")
async def get_all_collections(
    user: Annotated[User, Depends(get_current_user)],
) -> Sequence[Collection]:
    with Session(engine) as session:
        try:
            collections_list = collections.get_collections(session, user)
            logger.info("Retrieved all collections successfully.")
            return collections_list
        except Exception as e:
            logger.error(f"Failed to retrieve all collections: {e}")
            raise HTTPException(
                status_code=500, detail="Internal server error. Failed to retrieve all collections.")

# Get all collections for a user
@collections_router.get("/user")
async def get_user_collections(
    user: Annotated[User, Depends(get_current_user)],
) -> Sequence[CollectionInfo]:
    with Session(engine) as session:
        try:
            user_collections = [CollectionInfo.populate(
                col) for col in collections.get_collections_by_user(session, user)]
            logger.info("Retrieved user collections successfully.")
            return user_collections
        except Exception as e:
            logger.error(f"Failed to retrieve user collections: {e}")
            raise HTTPException(
                status_code=500, detail="Internal server error. Failed to retrieve user collections")

# TODO - maybe unnecessary due to the previous endpoint
@collections_router.get("/info")
async def get_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> CollectionInfo:
    with Session(engine) as session:
        collection = collections.get_collection_by_id(session, col_uuid, user)
        if collection is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        result = CollectionInfo.populate(collection)
        logger.info("Retrieved collection information successfully.")
        return result


@collections_router.get("/hierarchy")
async def get_collection_hierarchy(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> FolderIntake:
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        folder = collections.get_collection_hierarchy(session, col, user)
        if folder is None:
            logger.error("Collection hierarchy is corrupted.")
            raise HTTPException(status_code=404, detail="Collection hierarchy is corrupted")
        logger.info("Retrieved collection hierarchy successfully.")
        return folder

# TODO - test this
@collections_router.delete("/")
async def delete_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            logger.error("User does not have permission to write to this collection.")
            raise HTTPException(
                status_code=403, detail="You do not have permission to write to this collection")
        collections.delete_collection(session, col)
        logger.info("Collection deleted successfully.")
        return {"message": "Collection deleted successfully"}


# Add a user to the white-listed users for a collection
@collections_router.post("/permissions")
async def add_permission(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    permission: Permission,
    email: str,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            logger.error("User does not have permission to write to this collection.")
            raise HTTPException(
                status_code=403, detail="You do not have permission to write to this collection")
        db_user = users.get_user_by_email(session, email)
        # If creating for anonymous user
        if db_user is None:
            logger.error("User not found. Creating anonymous user.")
            db_user = users.create_anonymous_user(session, email)
        if db_user is None:
            logger.error("Anonymous user could not be created for given email.")
            raise HTTPException(
                status_code=404, detail="Anonymous user could not be created for given email.")
        collections.add_permission(session, col, db_user, permission, user)
        logger.info("Permission added successfully.")
        return {"message": "Permission added successfully"}


# Get white-listed users for a collection
@collections_router.get("/permissions")
async def get_permissions(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> Sequence[CollectionPermissionInfo]:
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            logger.error("User does not have permission to write to this collection.")
            raise HTTPException(
                status_code=403, detail="You do not have permission to write to this collection")
        permissions = collections.convert_user_id_to_email(session, col.permissions)
        logger.info("Retrieved permissions successfully.")
        return permissions


# Remove a user from the white-listed users for a collection
@collections_router.delete("/permissions")
async def remove_permission(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    email: str,
    permission: Permission,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            logger.error("User does not have permission to write to this collection.")
            raise HTTPException(
                status_code=403, detail="You do not have permission to write to this collection")
        db_user = users.get_user_by_email(session, email)
        if db_user is None:
            logger.error("User not found.")
            raise HTTPException(status_code=404, detail="User not found")
        collections.remove_permission(session, col, db_user, permission, user)
        logger.info("Permission removed successfully.")
        return {"message": "Permission removed successfully"}


# TODO - ability to filter documents by type, size or owner
# filter documents by type, size or owner
@collections_router.get("/{collection_uuid}/filter")
async def filter_documents(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    name: str | None = None,
    max_size: int | None = None,
    last_access: datetime | None = None,
):
    with Session(engine) as session:
        col = collections_router.get_collection_by_id(session, col_uuid, user)
        if col is None:
            logger.error("Collection not found.")
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user:
            logger.error("User is not the owner of this collection.")
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        documents = collections_router.filter_documents(session, col, name, max_size, last_access)
        if documents is None:
            logger.error("No documents found.")
            raise HTTPException(status_code=404, detail="No documents found")
        logger.info("Documents filtered successfully.")
        return documents

# Update collection name
@collections_router.put("/name")
async def update_collection_name(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    name: str
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            logger.error(f"Collection {col_uuid} not found")
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            logger.error(
                f"User {user.email} does not have permission to write to collection {col_uuid}")
            raise HTTPException(
                status_code=403, detail="You do not have permission to write to this collection")
        collections.update_collection_name(session, col, user, name)
        return {"message": "Collection name updated successfully"}

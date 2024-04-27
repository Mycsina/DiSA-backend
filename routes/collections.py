from datetime import datetime
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

import storage.collection as collections
import storage.user as users
from models.collection import Collection, CollectionInfo, Permission, SharedState
from models.folder import FolderIntake
from models.user import User
from storage.main import engine
from utils.security import get_current_user

collections_router = APIRouter(
    prefix="/collections",
    tags=["collections"],
)


@collections_router.post("/")
async def create_collection(
    user: Annotated[User, Depends(get_current_user)],
    manifest_hash: str | None = None,
    transaction_address: str | None = None,
    file: UploadFile = File(...),
    share_state: SharedState = SharedState.private,
):
    with Session(engine) as session:
        name = file.filename
        if name is None:
            raise HTTPException(status_code=400, detail="No file name provided")
        data = await file.read()
        collection = await collections.create_collection(
            session, name, data, user, share_state, manifest_hash, transaction_address
        )

        return {"message": "Collection created successfully", "uuid": collection.id}


@collections_router.get("/download")
async def download_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> FileResponse:
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_read(user):
            raise HTTPException(status_code=403, detail="You do not have permission to access this collection")
        file_path = await collections.download_collection(session, col, user)
        return FileResponse(
            file_path,
            filename=col.name,
        )


@collections_router.get("/")
async def get_all_collections(
    user: Annotated[User, Depends(get_current_user)],
) -> Sequence[Collection]:
    with Session(engine) as session:
        return collections.get_collections(session, user)


@collections_router.get("/user")
async def get_user_collections(
    user: Annotated[User, Depends(get_current_user)],
) -> Sequence[Collection]:
    with Session(engine) as session:
        return collections.get_collections_by_user(session, user)


@collections_router.get("/info")
async def get_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> CollectionInfo:
    with Session(engine) as session:
        collection = collections.get_collection_by_id(session, col_uuid, user)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        result = CollectionInfo.populate(collection)
        return result


@collections_router.get("/hierarchy")
async def get_collection_hierarchy(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
) -> FolderIntake:
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        folder = collections.get_collection_hierarchy(session, col, user)
        if folder is None:
            raise HTTPException(status_code=404, detail="Collection hierarchy is corrupted")
        return folder


@collections_router.delete("/")
async def delete_collection(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            raise HTTPException(status_code=403, detail="You do not have permission to write to this collection")
        collections.delete_collection(session, col)
        return {"message": "Collection deleted successfully"}


# TODO: test this
@collections_router.post("/permissions")
async def add_permission(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    user_uuid: UUID,
    permission: Permission,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            raise HTTPException(status_code=403, detail="You do not have permission to write to this collection")
        db_user = users.get_user_by_id(session, user_uuid)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        match permission:
            case Permission.read:
                collections.allow_read(session, db_user, col)
            case Permission.write:
                collections.allow_write(session, db_user, col)
            case Permission.view:
                collections.allow_view(session, db_user, col)
        return {"message": "Permission added successfully"}


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
        raise HTTPException(status_code=501, detail="Not implemented")
        col = collections_router.get_collection_by_id(session, col_uuid, user)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        documents = collections_router.filter_documents(session, col, name, max_size, last_access)
        if documents is None:
            raise HTTPException(status_code=404, detail="No documents found")
        return documents

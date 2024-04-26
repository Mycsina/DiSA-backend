from sqlite3 import IntegrityError
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session

import storage.collection as collections
from utils.exceptions import IntegrityBreach
from models.user import User
from utils.security import get_current_user
from storage.main import engine

documents_router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@documents_router.put("/documents/")
async def update_document(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
    file: UploadFile,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        doc = collections.get_document_by_id(session, doc_uuid)

        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc not in col.documents:
            raise HTTPException(status_code=404, detail="Document not in the specified collection")
        if not col.can_write(user):
            raise HTTPException(status_code=403, detail="You do not have permission to write to this collection")
        data = await file.read()
        try:
            collections.update_document(session, user, col, doc, data)
        except IntegrityError:
            raise IntegrityBreach("Document update failed. Verify the document hasn't already been updated")
        if doc.next is None:
            raise HTTPException(status_code=500, detail="Document update failed")
        return {"message": "Document updated successfully", "update_uuid": doc.next.id}


@documents_router.delete("/documents/")
async def delete_document(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        doc = collections.get_document_by_id(session, doc_uuid)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_write(user):
            raise HTTPException(status_code=403, detail="You do not have permission to write to this collection")
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc not in col.documents:
            raise HTTPException(status_code=404, detail="Document not in the specified collection")
        collections.delete_document(session, doc)
        return {"message": "Document deleted successfully"}


@documents_router.get("/documents/search")
async def search_documents(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    name: str,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if col.owner != user:
            raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
        documents = collections.search_documents(session, col, name)
        if documents is None:
            raise HTTPException(status_code=404, detail="No documents found")
        return documents


@documents_router.get("/documents/history")
async def get_document_history(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        col = collections.get_collection_by_id(session, col_uuid, user)
        doc = collections.get_document_by_id(session, doc_uuid)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        if not col.can_read(user):
            raise HTTPException(status_code=403, detail="You do not have permission to read this collection")
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc not in col.documents:
            raise HTTPException(status_code=404, detail="Document not in the specified collection")
        return collections.get_document_history(session, doc)

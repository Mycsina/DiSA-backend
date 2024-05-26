import logging
from sqlite3 import IntegrityError
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session

import storage.collection as collections
from models.user import User
from storage.main import engine
from utils.exceptions import IntegrityBreach
from utils.security import get_current_user

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

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
        try:
            col = collections.get_collection_by_id(session, col_uuid, user)
            doc = collections.get_document_by_id(session, doc_uuid)

            if col is None:
                logger.error(f"Collection not found.")
                raise HTTPException(status_code=404, detail="Collection not found")
            if doc is None:
                logger.error(f"Document not found.")
                raise HTTPException(status_code=404, detail="Document not found")
            if doc not in col.documents:
                logger.error(f"Document not in the specified collection.")
                raise HTTPException(status_code=404, detail="Document not in the specified collection")
            if not col.can_write(user):
                logger.error(f"This user does not have permission to write to this collection.")
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to write to this collection",
                )
            data = await file.read()
            collections.update_document(session, user, col, doc, data)
            if doc.next is None:
                logger.error(f"Document update failed.")
                raise HTTPException(status_code=500, detail="Document update failed")
            logger.info("Document updated successfully.")
            return {
                "message": "Document updated successfully",
                "update_uuid": doc.next.id,
            }
        except IntegrityError:
            logger.error("Document update failed due to an integrity error.")
            raise IntegrityBreach("Document update failed. Verify the document hasn't already been updated")
        except HTTPException as http_exception:
            logger.error(f"HTTP Exception ocurred: {http_exception}")
            raise http_exception
        except Exception as e:
            logger.error(f"An unexpected error ocurred: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@documents_router.delete("/documents/")
async def delete_document(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        try:
            col = collections.get_collection_by_id(session, col_uuid, user)
            doc = collections.get_document_by_id(session, doc_uuid)
            if col is None:
                logger.error("Collection not found.")
                raise HTTPException(status_code=404, detail="Collection not found")
            if not col.can_write(user):
                logger.error("The user does not have permission tp write to this collection.")
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to write to this collection",
                )
            if doc is None:
                logger.error("Document not found.")
                raise HTTPException(status_code=404, detail="Document not found")
            if doc not in col.documents:
                logger.error("Document not in the specified collection.")
                raise HTTPException(status_code=404, detail="Document not in the specified collection")
            collections.delete_document(session, doc)
            logger.info("Document deleted successfully.")
            return {"message": "Document deleted successfully"}
        except HTTPException as http_exception:
            logger.error(f"HTTP Exception occured: {http_exception}")
            raise http_exception
        except Exception as e:
            logger.error(f"An unexpected error occured: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@documents_router.get("/documents/search")
async def search_documents(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    name: str,
):
    with Session(engine) as session:
        try:
            col = collections.get_collection_by_id(session, col_uuid, user)
            if col is None:
                logger.error("Collection not found.")
                raise HTTPException(status_code=404, detail="Collection not found")
            if col.owner != user:
                logger.error("This user is not the owner of this collection.")
                raise HTTPException(status_code=403, detail="You are not the owner of this Collection")
            documents = collections.search_documents(session, col, name)
            if documents is None:
                logger.error("No documents found.")
                raise HTTPException(status_code=404, detail="No documents found")
            logger.info("Document found successfully.")
            return documents
        except HTTPException as http_exception:
            logger.error(f"HTTP Exception occured: {http_exception}")
            raise http_exception
        except Exception as e:
            logger.error(f"An unexpected error occured: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


@documents_router.get("/documents/history")
async def get_document_history(
    user: Annotated[User, Depends(get_current_user)],
    col_uuid: UUID,
    doc_uuid: UUID,
):
    with Session(engine) as session:
        try:
            col = collections.get_collection_by_id(session, col_uuid, user)
            doc = collections.get_document_by_id(session, doc_uuid)
            if col is None:
                logger.error("Collection not found.")
                raise HTTPException(status_code=404, detail="Collection not found")
            if not col.can_read(user):
                logger.error("This user does not have permission to read this collection.")
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to read this collection",
                )
            if doc is None:
                logger.error("Document not found.")
                raise HTTPException(status_code=404, detail="Document not found")
            if doc not in col.documents:
                logger.error("Document not found in the specified collection.")
                raise HTTPException(status_code=404, detail="Document not in the specified collection")
            logger.info("Document found successfully.")
            return collections.get_document_history(session, doc)
        except HTTPException as http_exception:
            logger.error(f"HTTP Exception occured: {http_exception}")
            raise http_exception
        except Exception as e:
            logger.error(f"An unexpected error occured: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

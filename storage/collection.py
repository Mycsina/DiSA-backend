import tarfile
import os
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from models.collection import Collection, Document
from models.folder import Folder
from models.user import User
from storage.main import TEMP_FOLDER, add_and_refresh
from storage.folder import walk_folder, create_folder


def get_collections(db: Session) -> Sequence[Collection]:
    statement = select(Collection)
    results = db.exec(statement)
    return results.all()


def get_collection_by_id(db: Session, col_id: UUID) -> Collection | None:
    statement = select(Collection).where(Collection.id == col_id)
    results = db.exec(statement)
    return results.first()


def get_document_by_id(db: Session, doc_id: UUID) -> Document | None:
    statement = select(Document).where(Document.id == doc_id)
    results = db.exec(statement)
    return results.first()


def create_collection(db: Session, name: str, data: bytes, user: User) -> Collection:
    if user.id is None:
        raise ValueError("User must have an ID to create a collection. This should never happen.")
    db_folder = Folder(name="root", owner_id=user.id)
    db_folder = add_and_refresh(db, db_folder)
    collection = Collection(name=name, owner=user.id, root=db_folder.id)
    collection = add_and_refresh(db, collection)

    if name.split(".")[-2].lower() == "tar":
        print(name.split(".")[-1].lower())
        # We're dealing with a zipped folder
        with open(f"{TEMP_FOLDER}/{name}", "wb") as f:
            f.write(data)
        with tarfile.open(f"{TEMP_FOLDER}/{name}") as tar:
            tar.extractall(f"{TEMP_FOLDER}")
        os.remove(f"{TEMP_FOLDER}/{name}")
        # Create the folder structure, walking through the extracted files
        root = walk_folder(f"{TEMP_FOLDER}/{name.split('.')[0]}", user)
        create_folder(db, root, collection.id)
    else:
        # We're dealing with a single document
        doc = Document(name=name, size=len(data), folder_id=db_folder.id, collection_id=collection.id)
        doc = add_and_refresh(db, doc)

    return collection


def update_document(db: Session, col_id: UUID, doc_id: UUID, file: bytes):
    collection = get_collection_by_id(db, col_id)
    if collection is None:
        raise ValueError("Collection not found")
    document = get_document_by_id(db, doc_id)
    if document is None:
        raise ValueError("Document not found")
    if document.folder.collection_id != col_id:
        raise ValueError("Document not in the specified collection")

    document.data = file
    document.size = len(file)
    db.commit()
    return document


def delete_document(db: Session, col_id: UUID, doc_id: UUID):
    collection = get_collection_by_id(db, col_id)
    if collection is None:
        raise ValueError("Collection not found")
    document = get_document_by_id(db, doc_id)
    if document is None:
        raise ValueError("Document not found")
    if document.folder.collection_id != col_id:
        raise ValueError("Document not in the specified collection")

    # db.query(Document).filter(Document.id == doc_id).delete()
    db.commit()
    return True


def delete_collection(db: Session, col_id: UUID):
    collection = get_collection_by_id(db, col_id)
    if collection is None:
        raise ValueError("Collection not found")
    db.delete(collection)
    db.commit()
    return True

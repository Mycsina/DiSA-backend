import os
import tarfile
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from models.collection import Collection, Document, SharedState
from models.event import Event, EventTypes
from models.folder import Folder
from models.user import User
from storage.folder import create_folder, walk_folder
from storage.main import TEMP_FOLDER, add_and_refresh


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


def create_collection(db: Session, name: str, data: bytes, user: User, share_state: SharedState) -> Collection:
    if user.id is None:
        raise ValueError("User must have an ID to create a collection. This should never happen.")

    # Create the root folder for the collection
    db_folder = Folder(name="root", owner_id=user.id)
    db_folder = add_and_refresh(db, db_folder)

    # Create the collection
    collection = Collection(name=name, owner=user.id, root=db_folder.id, share_state=share_state)
    collection = add_and_refresh(db, collection)

    if name.split(".")[-2].lower() == "tar":
        print(name.split(".")[-1].lower())
        # We're dealing with a zipped folder
        with open(f"{TEMP_FOLDER}/{name}", "wb") as f:
            f.write(data)
        with tarfile.open(f"{TEMP_FOLDER}/{name}") as tar:
            # TODO - replace deprecated method
            tar.extractall(f"{TEMP_FOLDER}")
        os.remove(f"{TEMP_FOLDER}/{name}")
        # Create the folder structure, walking through the extracted files
        root = walk_folder(f"{TEMP_FOLDER}/{name.split('.')[0]}", user)
        create_folder(db, root, collection.id)

    else:
        # We're dealing with a single document
        doc = Document(name=name, size=len(data), folder_id=db_folder.id, collection_id=collection.id)
        doc.events.append(Event(type=EventTypes.Create, user_id=user.id, document_id=doc.id))
        doc = add_and_refresh(db, doc)

    return collection


# TODO - verify that this is correct
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


# TODO - verify that this is correct
def delete_document(db: Session, doc_id: UUID):
    document = get_document_by_id(db, doc_id)
    if document is None:
        raise ValueError("Document not found")

    db.commit()
    return True


# TODO - verify that this is correct
def delete_collection(db: Session, col_id: UUID):
    collection = get_collection_by_id(db, col_id)
    if collection is None:
        raise ValueError("Collection not found")
    db.delete(collection)
    db.commit()
    return True

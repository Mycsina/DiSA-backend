import os
import tarfile
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from models.collection import Collection, Document, SharedState
from models.event import EventTypes
from models.folder import Folder, FolderIntake
from models.update import Update
from models.user import User
from storage.event import register_event
from storage.folder import create_folder, recreate_structure, walk_folder
from storage.main import TEMP_FOLDER


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

    collection = Collection(name=name, share_state=share_state)
    db_folder = Folder(name=name)
    register_event(db, collection, user, EventTypes.Create)
    collection.owner = user
    collection.folder = db_folder
    db.add(collection)

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
        db_folder = create_folder(db, root, db_folder)

    else:
        # We're dealing with a single document
        doc = Document(name=name, size=len(data), folder_id=db_folder.id, collection_id=collection.id)
        register_event(db, doc, user, EventTypes.Create)
        db.add(doc)
    db.commit()
    return collection


def get_collection_hierarchy(db: Session, col: Collection) -> FolderIntake | None:
    structure = recreate_structure(db, col.folder)
    return structure


def update_document(db: Session, user: User, col_id: UUID, doc_id: UUID, file: bytes):
    document = get_document_by_id(db, doc_id)
    if document is None:
        raise ValueError("Document not found. This should never happen.")
    new_document = Document(
        name=document.name,
        size=len(file),
        folder_id=document.folder_id,
        collection_id=col_id,
        access_from_date=document.access_from_date,
    )
    update = Update(user_id=user.id, previous_id=document.id, updated_id=new_document.id)
    db.add(update)
    db.add(new_document)
    db.commit()
    return document


# TODO - verify that this is correct
def delete_document(db: Session, doc: Document):
    register_event(db, doc, doc.collection.owner, EventTypes.Delete)
    db.commit()
    return True


# TODO - verify that this is correct
def delete_collection(db: Session, col: Collection):
    register_event(db, col, col.owner, EventTypes.Delete)
    db.commit()
    return True


def search_documents(db: Session, col: Collection, name: str) -> list[Document] | None:
    docs = [doc for doc in col.documents if doc.name == name and doc.next is None]
    if len(docs) == 0:
        return None
    return docs

import hashlib
import io
import tarfile
from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

import storage.paperless as ppl
from models.collection import Collection, Document, SharedState
from models.event import DocumentEvent, EventTypes
from models.folder import Folder, FolderIntake
from models.update import Update
from models.user import User
from security import verify_manifest
from storage.event import register_event
from storage.folder import (
    create_folder,
    populate_documents,
    recreate_structure,
    walk_folder,
)
from storage.main import TEMP_FOLDER


def get_collections(db: Session, user: User) -> Sequence[Collection]:
    statement = select(Collection)
    results = db.exec(statement)
    collections = results.all()
    collections = [col for col in collections if not col.is_deleted()]
    for col in collections:
        register_event(db, col, user, EventTypes.Access)
    return collections


def get_collections_by_user(db: Session, user: User) -> Sequence[Collection]:
    statement = select(Collection).where(Collection.owner_id == user.id)
    results = db.exec(statement)
    collections = results.all()
    collections = [col for col in collections if not col.is_deleted()]
    for col in collections:
        register_event(db, col, user, EventTypes.Access)
    return collections


def get_collection_by_id(db: Session, col_id: UUID, user: User) -> Collection | None:
    statement = select(Collection).where(Collection.id == col_id)
    results = db.exec(statement)
    collection = results.first()
    if collection is not None:
        if collection.is_deleted():
            return None
    return collection


def get_document_by_id(db: Session, doc_id: UUID) -> Document | None:
    statement = select(Document).where(Document.id == doc_id)
    results = db.exec(statement)
    document = results.first()
    return document


async def create_collection(
    db: Session,
    name: str,
    data: bytes,
    user: User,
    share_state: SharedState,
    manifest_hash: str,
    transaction_address: str,
) -> Collection:

    # Check manifest hash against the blockchain event
    if not verify_manifest(manifest_hash, transaction_address):
        raise AssertionError("Manifest hash does not match the transaction address")

    # Create the collection in the database
    collection = Collection(name=name, share_state=share_state)
    db_folder = Folder(name=name)
    collection.owner = user
    collection.folder = db_folder
    register_event(db, collection, user, EventTypes.Create)

    # Create the collection in Paperless-ngx
    await ppl.create_collection(db, collection, name=name)

    # We're dealing with a zipped folder
    if name.split(".")[-2].lower() == "tar":
        f = io.BytesIO(data)
        with tarfile.open(fileobj=f) as tar:
            tar.extractall(f"{TEMP_FOLDER}", filter="data")
        # Create the folder structure, walking through the extracted files
        folder_name = f"{TEMP_FOLDER}/{name.split('.')[0]}"
        root = walk_folder(folder_name, user)
        # Create the folder structure in the database
        mappings = create_folder(db, root, db_folder)
        # Ingest the documents into Paperless-ngx
        await ppl.upload_folder(db, mappings, collection, user)

    # We're dealing with a single document
    else:
        # Create the document in the database
        file_hash = hashlib.sha256(data).hexdigest()
        doc = Document(name=name, size=len(data), folder_id=db_folder.id, collection_id=collection.id, hash=file_hash)
        register_event(db, doc, user, EventTypes.Create)
        db.add(doc)
        # Add UUID to avoid duplicates
        data = data + str(doc.id).encode()
        # Create the document in Paperless-ngx
        await ppl.create_single_document(db, data, doc, collection, user, name=name, data=data)

    db.add(collection)
    db.commit()
    return collection


def get_collection_hierarchy(db: Session, col: Collection, user: User) -> FolderIntake:
    structure = recreate_structure(db, col.folder, user)
    return structure


def update_document(db: Session, user: User, col: Collection, doc: Document, file: bytes):
    file_hash = hashlib.sha256(file).hexdigest()
    new_document = Document(
        name=doc.name,
        size=len(file),
        folder_id=doc.folder_id,
        collection_id=col.id,
        access_from_date=doc.access_from_date,
        hash=file_hash,
    )
    update = Update(user_id=user.id, previous_id=doc.id, updated_id=new_document.id)
    db.add(update)
    db.add(new_document)
    db.commit()
    return doc


def delete_document(db: Session, doc: Document):
    register_event(db, doc, doc.collection.owner, EventTypes.Delete)
    db.commit()
    return True


def delete_collection(db: Session, col: Collection):
    register_event(db, col, col.owner, EventTypes.Delete)
    db.commit()
    return True


def search_documents(db: Session, col: Collection, name: str) -> list[Document] | None:
    docs = [doc for doc in col.documents if doc.name == name and doc.next is None]
    for doc in docs:
        register_event(db, doc, col.owner, EventTypes.Access)
    if len(docs) == 0:
        return None
    return docs


def filter_documents(
    db: Session, col: Collection, name: str | None, max_size: int | None, last_access: datetime | None
):
    statement = select(Document).where(Document.collection_id == col.id)
    if name is not None:
        statement = statement.where(Document.name == name)
    if max_size is not None:
        statement = statement.where(Document.size <= max_size)
    results = db.exec(statement)
    documents = results.all()
    if last_access is not None:
        documents = [doc for doc in documents if doc.last_access() >= last_access]
    for doc in documents:
        register_event(db, doc, col.owner, EventTypes.Access)
    return documents


def get_document_history(db: Session, doc: Document) -> list[Update | DocumentEvent]:
    events = []
    while doc.next is not None:
        events.append(doc.next)
        events.extend(doc.events)
        doc = doc.next.new
    events.sort(key=lambda x: x.timestamp, reverse=True)
    return events


async def download_collection(db: Session, col: Collection, user: User) -> FolderIntake:
    structure = recreate_structure(db, col.folder, user)
    structure = await populate_documents(db, structure)
    return structure

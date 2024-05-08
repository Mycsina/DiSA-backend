import hashlib
import io
import tarfile
from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

import storage.paperless as ppl
from models.collection import (
    Collection,
    CollectionPermission,
    CollectionPermissionInfo,
    Document,
    Permission,
)
from models.event import DocumentEvent, EventTypes
from models.folder import Folder, FolderIntake
from models.update import Update
from models.user import User
from storage.event import register_event
from storage.folder import (
    create_folder,
    populate_documents,
    recreate_structure,
    walk_folder,
    write_folder,
)
from storage.main import TEMP_FOLDER
from storage.user import get_user_by_id
from utils.security import verify_manifest


def get_collections(db: Session, user: User) -> Sequence[Collection]:
    statement = select(Collection)
    results = db.exec(statement)
    collections = results.all()
    # Remove deleted collections
    collections = [col for col in collections if not col.is_deleted()]
    # Verify user can view these collections
    collections = [col for col in collections if col.can_view(user)]
    for col in collections:
        register_event(db, col, user, EventTypes.Access)
    return collections


def get_collections_by_user(db: Session, user: User) -> Sequence[Collection]:
    statement = select(Collection).where(Collection.owner_id == user.id)
    results = db.exec(statement)
    collections = results.all()
    # Remove deleted collections
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
    transaction_address: str,
) -> Collection:

    # Check manifest hash against the blockchain event
    # if not verify_manifest(manifest_hash, transaction_address):
    #     raise AssertionError("Manifest hash does not match the transaction address")

    # Create the collection in the database
    collection = Collection(name=name)
    db_folder = Folder(name=name, collection_id=collection.id)
    collection.owner = user
    collection.folder = db_folder
    register_event(db, collection, user, EventTypes.Create)

    # Create the collection in Paperless-ngx
    await ppl.create_collection(db, collection, name=name)

    # Extract tarfile containing signature, manifest and files
    archive_name = name.split(".")[0]
    f = io.BytesIO(data)
    folder_name = f"{TEMP_FOLDER}/{archive_name}"
    with tarfile.open(fileobj=f) as tar:
        tar.extractall(folder_name, filter="data")

    with open(folder_name + "/hashes.asics", "rb") as f:
        signature = f.read()

    with open(folder_name + "/hashes.json", "rb") as f:
        hashes = f.read()

    root = walk_folder(folder_name + "/archive", user)
    # Create the folder structure in the database
    mappings = create_folder(db, root, db_folder)
    # Ingest the documents into Paperless-ngx
    await ppl.upload_folder(db, mappings, collection, user)

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


async def download_collection(db: Session, col: Collection, user: User) -> str:
    structure = recreate_structure(db, col.folder, user)
    structure = await populate_documents(db, structure)

    folder_path = f"{TEMP_FOLDER}/{col.name}"
    write_folder(structure, folder_path)
    with open(folder_path + ".tar", "wb") as tar:
        with tarfile.open(fileobj=tar, mode="w") as tar:
            tar.add(folder_path, arcname=col.name)

    return folder_path + ".tar"


def allow_read(db: Session, user: User, col: Collection, creator: User):
    perm = CollectionPermission(
        user_id=user.id, collection_id=col.id, permission=Permission.read, creator_id=creator.id
    )
    db.add(perm)
    db.commit()


def allow_write(db: Session, user: User, col: Collection, creator: User):
    perm = CollectionPermission(
        user_id=user.id, collection_id=col.id, permission=Permission.write, creator_id=creator.id
    )
    db.add(perm)
    db.commit()


def allow_view(db: Session, user: User, col: Collection, creator: User):
    perm = CollectionPermission(
        user_id=user.id, collection_id=col.id, permission=Permission.view, creator_id=creator.id
    )
    db.add(perm)
    db.commit()


def convert_user_id_to_email(db: Session, perms: list[CollectionPermission]) -> list[CollectionPermissionInfo]:
    result = []
    for perm in perms:
        user = get_user_by_id(db, perm.user_id)
        creator = get_user_by_id(db, perm.creator_id)
        if user is None or creator is None:
            raise LookupError("This should never happen.")
        info = CollectionPermissionInfo(
            collection_id=perm.collection_id,
            email=user.email,
            creator_email=creator.email,
            permission=perm.permission,
        )
        result.append(info)
    return result


def add_permission(db: Session, col: Collection, user: User, permission: Permission, creator: User):
    match permission:
        case Permission.read:
            allow_read(db, user, col, creator)
        case Permission.write:
            allow_write(db, user, col, creator)
        case Permission.view:
            allow_view(db, user, col, creator)


def remove_permission(db: Session, col: Collection, user: User, permission: Permission, executor: User):
    statement = (
        select(CollectionPermission)
        .where(CollectionPermission.collection_id == col.id)
        .where(CollectionPermission.user_id == user.id)
        .where(CollectionPermission.creator_id == executor.id)
        .where(CollectionPermission.permission == permission)
    )
    results = db.exec(statement)
    perm = results.first()
    db.delete(perm)
    db.commit()
    return True

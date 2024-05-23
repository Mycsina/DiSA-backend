import logging
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

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def get_collections(db: Session, user: User) -> Sequence[Collection]:
    logger.debug(f"Retrieving collections for user {user.id}.")
    statement = select(Collection)
    results = db.exec(statement)
    collections = results.all()
    # Remove deleted collections
    collections = [col for col in collections if not col.is_deleted()]
    # Verify user can view these collections
    collections = [col for col in collections if col.can_view(user)]
    for col in collections:
        register_event(db, col, user, EventTypes.Access)
    logger.debug(f"Retrieved {len(collections)} collections for user {user.id}.")
    return collections


def get_collections_by_user(db: Session, user: User) -> Sequence[Collection]:
    logger.debug(f"Retrieving collections owned by user {user.id}.")
    statement = select(Collection).where(Collection.owner_id == user.id)
    results = db.exec(statement)
    collections = results.all()
    # Remove deleted collections
    collections = [col for col in collections if not col.is_deleted()]
    for col in collections:
        register_event(db, col, user, EventTypes.Access)
    logger.debug(f"Retrieved {len(collections)} collections owned by user {user.id}.")
    return collections


def get_collection_by_id(db: Session, col_id: UUID, user: User) -> Collection | None:
    logger.debug(f"Retrieving collection with ID {col_id} for user {user.id}.")
    statement = select(Collection).where(Collection.id == col_id)
    results = db.exec(statement)
    collection = results.first()
    if collection is not None:
        if collection.is_deleted():
            logger.warning(f"Collection {col_id} is deleted.")
            return None
    logger.debug(f"Retrieved collection with ID {col_id} for user {user.id}.")
    return collection


def get_document_by_id(db: Session, doc_id: UUID) -> Document | None:
    logger.debug(f"Retrieving document with ID {doc_id}.")
    statement = select(Document).where(Document.id == doc_id)
    results = db.exec(statement)
    document = results.first()
    if document is None:
        logger.warning(f"Document with ID {doc_id} not found.")
    else:
        logger.debug(f"Retrieved document with ID {doc_id}.")
    return document


async def create_collection(
    db: Session,
    name: str,
    data: bytes,
    user: User,
    transaction_address: str,
) -> Collection:

    logger.debug(f"Creating collection {name} for user {user.id}.")

    # Create the collection in the database
    collection = Collection(name=name)
    db_folder = Folder(name=name, collection_id=collection.id)
    collection.owner = user
    collection.folder = db_folder
    register_event(db, collection, user, EventTypes.Create)
    logger.debug(f"Collection '{name}' created in the database.")

    # Create the collection in Paperless-ngx
    await ppl.create_collection(db, collection, name=name)
    logger.debug(f"Collection '{name}' created in Paperless-ngx.")

    # Extract tarfile containing signature, manifest and files
    archive_name = name.split(".")[0]
    f = io.BytesIO(data)
    folder_name = f"{TEMP_FOLDER}/{archive_name}"
    with tarfile.open(fileobj=f) as tar:
        tar.extractall(folder_name, filter="data")
    logger.debug(f"Extracted tarfile to {folder_name} successfully.")

    logger.debug("Reading signature and hashes from extracted files.")
    with open(folder_name + "/hashes.asics", "rb") as f:
        signature = f.read()
    collection.signature = signature

    with open(folder_name + "/hashes.json", "r") as f:
        hashes = f.read()
    collection.manifest = hashes
    manifest_hash = hashlib.sha256(hashes.encode()).hexdigest()
    logger.debug("Read signature and hashes successfully.")

    # Check manifest hash against the blockchain event
    logger.debug("Verifying manifest hash against the blockchain event.")
    if not verify_manifest(manifest_hash, transaction_address):
        logger.error("Manifest hash does not match the transaction address.")
        raise AssertionError("Manifest hash does not match the transaction address")

    logger.debug("Walking the folder structure and creating it in the database.")
    root = walk_folder(folder_name + "/archive", user)
    # Create the folder structure in the database
    mappings = create_folder(db, root, db_folder)
    # Ingest the documents into Paperless-ngx
    logger.debug("Uploading documents into Paperless-ngx.")
    await ppl.upload_folder(db, mappings, collection, user)

    db.add(collection)
    db.commit()
    logger.debug(f"Collection '{name}' created successfully.")
    return collection


def get_collection_hierarchy(db: Session, col: Collection, user: User) -> FolderIntake:
    logger.debug(f"Retrieving hierarchy for collection {col.id} for user {user.id}.")
    structure = recreate_structure(db, col.folder, user)
    logger.debug(f"Hierarchy retrieved successfully for collection {col.id} by user {user.id}.")
    return structure


def update_document(db: Session, user: User, col: Collection, doc: Document, file: bytes):
    logger.debug(f"Updating document {doc.id} in collection {col.id} by user {user.id}.")
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
    logger.debug(f"Document {doc.id} updated successfully in collection {col.id} by user {user.id}.")
    return doc


def delete_document(db: Session, doc: Document):
    logger.debug(f"Deleting document {doc.id} from collection {doc.collection_id}.")
    register_event(db, doc, doc.collection.owner, EventTypes.Delete)
    db.commit()
    logger.debug(f"Document {doc.id} deleted successfully from collection {doc.collection_id}.")
    return True


def delete_collection(db: Session, col: Collection):
    logger.debug(f"Deleting collection {col.id}.")
    register_event(db, col, col.owner, EventTypes.Delete)
    db.commit()
    logger.debug(f"Collection {col.id} deleted successfully.")
    return True


def search_documents(db: Session, col: Collection, name: str) -> list[Document] | None:
    logger.debug(f"Searching for documents with name {name} in collection {col.id}.")
    docs = [doc for doc in col.documents if doc.name == name and doc.next is None]
    for doc in docs:
        register_event(db, doc, col.owner, EventTypes.Access)
    if len(docs) == 0:
        logger.warning(f"No documents found with name {name} in collection {col.id}.")
        return None
    logger.debug(f"Found {len(docs)} documents with name {name} in collection {col.id}.")
    return docs


def filter_documents(
    db: Session, col: Collection, name: str | None, max_size: int | None, last_access: datetime | None
):
    logger.debug(f"Filtering documents in collection {col.id}.")
    statement = select(Document).where(Document.collection_id == col.id)
    if name is not None:
        logger.debug(f"Applying name filter: {name}.")
        statement = statement.where(Document.name == name)
    if max_size is not None:
        logger.debug(f"Applying max size filter: {max_size}.")
        statement = statement.where(Document.size <= max_size)
    results = db.exec(statement)
    documents = results.all()
    if last_access is not None:
        logger.debug(f"Applying last access filter: {last_access}.")
        documents = [doc for doc in documents if doc.last_access() >= last_access]
    for doc in documents:
        register_event(db, doc, col.owner, EventTypes.Access)
    logger.debug(f"Filtered {len(documents)} documents in collection {col.id}.")
    return documents


def get_document_history(db: Session, doc: Document) -> list[Update | DocumentEvent]:
    logger.debug(f"Retrieving history for document {doc.id}.")
    events = []
    while doc.next is not None:
        events.append(doc.next)
        events.extend(doc.events)
        doc = doc.next.new
    events.sort(key=lambda x: x.timestamp, reverse=True)
    logger.debug(f"History retrieved successfully for document {doc.id}.")
    return events


async def download_collection(db: Session, col: Collection, user: User) -> str:
    logger.debug(f"Downloading collection {col.id} by user {user.id}.")
    structure = recreate_structure(db, col.folder, user)
    structure = await populate_documents(db, structure)

    folder_path = f"{TEMP_FOLDER}/{col.name}"
    write_folder(structure, folder_path)
    with open(folder_path + ".tar", "wb") as tar:
        with tarfile.open(fileobj=tar, mode="w") as tar:
            tar.add(folder_path, arcname=col.name)

    logger.debug(f"Collection {col.id} downloaded successfully by user {user.id}.")
    return folder_path + ".tar"


def allow_read(db: Session, user: User, col: Collection, creator: User):
    logger.debug(f"Allowing user {user.id} to read collection {col.id} by creator {creator.id}.")
    perm = CollectionPermission(
        user_id=user.id, collection_id=col.id, permission=Permission.read, creator_id=creator.id
    )
    db.add(perm)
    db.commit()
    logger.debug(f"User {user.id} allowed to read collection {col.id} by creator {creator.id}.")


def allow_write(db: Session, user: User, col: Collection, creator: User):
    logger.debug(f"Allowing user {user.id} to write collection {col.id} by creator {creator.id}.")
    perm = CollectionPermission(
        user_id=user.id, collection_id=col.id, permission=Permission.write, creator_id=creator.id
    )
    db.add(perm)
    db.commit()
    logger.debug(f"User {user.id} allowed to write collection {col.id} by creator {creator.id}.")


def allow_view(db: Session, user: User, col: Collection, creator: User):
    logger.debug(f"Allowing user {user.id} to view collection {col.id} by creator {creator.id}.")
    perm = CollectionPermission(
        user_id=user.id, collection_id=col.id, permission=Permission.view, creator_id=creator.id
    )
    db.add(perm)
    db.commit()
    logger.debug(f"User {user.id} allowed to view collection {col.id} by creator {creator.id}.")


def convert_user_id_to_email(db: Session, perms: list[CollectionPermission]) -> list[CollectionPermissionInfo]:
    logger.debug("Converting user IDs to emails.")
    result = []
    for perm in perms:
        user = get_user_by_id(db, perm.user_id)
        creator = get_user_by_id(db, perm.creator_id)
        if user is None or creator is None:
            logger.error("User or creator not found.")
            raise LookupError("This should never happen.")
        info = CollectionPermissionInfo(
            collection_id=perm.collection_id,
            email=user.email,
            creator_email=creator.email,
            permission=perm.permission,
        )
        result.append(info)
    logger.debug("Converted user IDs to emails successfully.")
    return result


def add_permission(db: Session, col: Collection, user: User, permission: Permission, creator: User):
    logger.debug(f"Adding permission {permission} to user {user.id} in collection {col.id} by creator {creator.id}.")
    match permission:
        case Permission.read:
            logger.debug("Adding read permission.")
            allow_read(db, user, col, creator)
        case Permission.write:
            logger.debug("Adding write permission.")
            allow_write(db, user, col, creator)
        case Permission.view:
            logger.debug("Adding view permission.")
            allow_view(db, user, col, creator)


def remove_permission(db: Session, col: Collection, user: User, permission: Permission, executor: User):
    logger.debug(
        f"Removing permission {permission} from user {user.id} in collection {col.id} by executor {executor.id}."
    )
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
    logger.debug(
        f"Permission {permission} removed successfully from user {user.id} in collection {col.id} by executor {executor.id}."  # noqa
    )
    return True


def update_collection_name(db: Session, col: Collection, user: User, name: str):
    if col.owner_id != user.id:
        logger.error(f"User {user.id} is not the owner of collection {col.id}.")
        raise PermissionError("Only the owner can update the collection name.")
    if col.is_deleted():
        logger.error(f"Collection {col.id} is deleted.")
        raise ValueError("Cannot update a deleted collection.")
    if not (3 < len(name) < 50):
        logger.error(f"Name {name} is not between 4 and 50 characters.")
        raise ValueError("Name must be between 4 and 50 characters.")
    if col.name == name:
        return col
    col.name = name
    db.add(col)
    db.commit()
    logger.debug(f"Collection {col.id} name updated successfully by user {user.id}.")
    return col

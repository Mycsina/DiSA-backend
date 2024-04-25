from uuid import UUID

from sqlmodel import Session

import storage.collection
from models.collection import Collection, Document, EDocumentIntake
from models.paperless import CollectionPaperless, DocumentPaperless, UserPaperless
from models.user import User
from paperless import create_correspondent
from paperless import create_document as ppl_create_document
from paperless import create_tag


async def create_user(db: Session, user: User, **kwargs):
    """
    Create a user/correspondent in Paperless-ngx.

    For kwargs usage, see the create_correspondent function documentation.
    """
    name = user.email + "-" + str(user.id)
    correspondent_id = await create_correspondent(name=name)
    user.paperless = UserPaperless(paperless_id=correspondent_id)
    db.add(user)


async def create_collection(db: Session, collection: Collection, **kwargs):
    """
    Create a collection/tag in Paperless-ngx.

    For kwargs usage, see the create_tag function documentation.
    """
    name = collection.name + "-" + str(collection.id)
    tag_id = await create_tag(name=name)
    collection.paperless = CollectionPaperless(paperless_id=tag_id)
    db.add(collection)


async def create_document(db: Session, document: EDocumentIntake, collection: Collection, user: User, **kwargs):
    """
    Create a document in Paperless-ngx.

    For kwargs usage, see the create_document function documentation.
    """
    if collection.paperless is None:
        raise ValueError("Given collection has no paperless representation")
    tag_id = collection.paperless.paperless_id
    correspondent_id = user.paperless.paperless_id  # type: ignore
    doc_id = await ppl_create_document(
        title=document.name,
        document=document.content,
        correspondent=correspondent_id,
        tags=tag_id,
    )
    doc_id = UUID(doc_id)
    doc = storage.collection.get_document_by_id(db, document.doc_id)
    if doc is None:
        raise ValueError(f"Document with id {document.doc_id} not found. Mapping is corrupted.")
    doc.paperless = DocumentPaperless(paperless_id=doc_id)
    db.add(doc)


async def create_single_document(
    db: Session, content: bytes, document: Document, collection: Collection, user: User, **kwargs
):
    """
    Create a document in Paperless-ngx.

    For kwargs usage, see the create_document function documentation.
    """
    if collection.paperless is None:
        raise ValueError("Given collection has no paperless representation")
    tag_id = collection.paperless.paperless_id
    correspondent_id = user.paperless.paperless_id  # type: ignore
    doc_id = await ppl_create_document(
        title=document.name,
        document=content,
        correspondent=correspondent_id,
        tags=tag_id,
    )
    doc_id = UUID(doc_id)
    document.paperless = DocumentPaperless(paperless_id=doc_id)
    db.add(document)


async def upload_folder(db: Session, mappings: list[EDocumentIntake], collection: Collection, user: User, **kwargs):
    """
    Create all documents in Paperless-ngx.
    """
    for mapping in mappings:
        await create_document(db, mapping, collection, user)
    return collection

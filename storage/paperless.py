from uuid import UUID

from sqlmodel import Session

from models.collection import Collection, Document, DocumentIntake
from models.folder import FolderIntake
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
    with db as session:
        session.add(user)


async def create_collection(db: Session, collection: Collection, **kwargs):
    """
    Create a collection/tag in Paperless-ngx.

    For kwargs usage, see the create_tag function documentation.
    """
    name = collection.name + "-" + str(collection.id)
    tag_id = await create_tag(name=name)
    collection.paperless = CollectionPaperless(paperless_id=tag_id)
    db.add(collection)


async def create_document(db: Session, document: DocumentIntake, collection: Collection, user: User, **kwargs):
    """
    Create a document in Paperless-ngx.

    For kwargs usage, see the create_document function documentation.
    """
    if collection.paperless is None:
        raise ValueError("Given collection has no paperless representation")
    tag_id = collection.paperless_id
    correspondent_id = user.paperless_id
    doc_id = await ppl_create_document(
        title=document.name,
        document=document.content,
        correspondent=correspondent_id,
        tags=tag_id,
    )
    doc_id = UUID(doc_id)
    document.paperless = DocumentPaperless(paperless_id=doc_id)
    db.add(document)


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


async def upload_folder(db: Session, folder: FolderIntake, collection: Collection, user: User, **kwargs):
    """
    Traverse the folder structure and upload all documents to Paperless-ngx.
    This will squash the folder structure into a flat list of documents in Paperless-ngx.
    """
    for item in folder.children:
        if isinstance(item, DocumentIntake):
            await create_document(db, item, collection, user)
        elif isinstance(item, FolderIntake):
            await upload_folder(db, item, collection, user)
        else:
            raise ValueError("Unknown item type")

import hashlib
import os

from sqlmodel import Session

from models.collection import Document, DocumentIntake, EDocumentIntake
from models.event import EventTypes
from models.folder import Folder, FolderIntake
from models.user import User
from storage.event import register_event
from storage.paperless import download_document


def recreate_structure(db: Session, root: Folder, user: User) -> FolderIntake:
    """Recreate the FolderIntake structure from the structure in the database."""
    root_folder = FolderIntake(name=root.name)
    for child in root.sub_folders:
        root_folder.children.append(recreate_structure(db, child, user))
    for doc in root.documents:
        deleted = False
        if doc.is_deleted():
            deleted = True
        # Travel until the last update, if any is deleted, the document is considered deleted
        while doc.next is not None and not deleted:
            if doc.is_deleted():
                deleted = True
            doc = doc.next.new
        register_event(db, doc, user, EventTypes.Access)
        if not deleted:
            # TODO: This is the worst way to do this, literally wrong object type but it works
            root_folder.children.append(doc)  # type: ignore
    return root_folder


async def populate_documents(db: Session, root: FolderIntake) -> FolderIntake:
    """
    Populate DocumentIntake objects with their actual content.
    """
    new_root = FolderIntake(name=root.name)
    for child in root.children:
        if isinstance(child, FolderIntake):
            folder = await populate_documents(db, child)
            new_root.children.append(folder)
        # TODO: Tied to the wrong implementation above, but might as well take advantage of it
        elif isinstance(child, Document):
            new_doc = await download_document(db, child)
            new_root.children.append(new_doc)
        elif isinstance(child, DocumentIntake):
            raise TypeError("Please only call this with a FolderIntake from recreate_structure")
    return new_root


def write_folder(root: FolderIntake, path: str):
    """Write the FolderIntake structure to the given path."""
    os.makedirs(path, exist_ok=True)
    for child in root.children:
        if isinstance(child, FolderIntake):
            write_folder(child, os.path.join(path, child.name))
        else:
            with open(os.path.join(path, child.name), "wb") as file:
                file.write(child.content)


# TODO: saving all file content in memory is not a good idea
def walk_folder(root: str, user: User) -> FolderIntake:
    """Walk through the given root path and create a tree of FolderIntake and DocumentIntake objects."""
    name = os.path.basename(root)
    folder = FolderIntake(name=name)
    for item in os.listdir(root):
        item_path = os.path.join(root, item)
        if os.path.isdir(item_path):
            folder.children.append(walk_folder(item_path, user))
        else:
            content = open(item_path, "rb").read()
            file_hash = hashlib.sha256(content).hexdigest()
            folder.children.append(
                DocumentIntake(
                    name=item,
                    size=os.path.getsize(item_path),
                    content=content,
                    hash=file_hash,
                    parent_folder=folder,
                )
            )
    return folder


def create_folder(db: Session, root: FolderIntake, db_root: Folder) -> list[EDocumentIntake]:
    """
    Creates Folder and Document structures in the database from the given root FolderIntake object.
    Returns a mapping of the DocumentIntake objects to their corresponding Document objects in the database.
    """
    root_id = db_root.id
    if root_id is None:
        raise ValueError("Could not create root folder")
    children = root.children
    parents = [db_root] * len(children)
    mapping: list[EDocumentIntake] = []
    while len(children) > 0:
        child = children.pop()
        parent = parents.pop()
        if isinstance(child, FolderIntake):
            db_child = Folder(name=child.name, collection_id=db_root.collection.id, parent_id=parent.id)
            parent.sub_folders.append(db_child)
            db.add(db_child)
            parents.extend([db_child] * len(child.children))
            children.extend(child.children)
        else:
            db_child = Document(
                name=child.name,
                size=child.size,
                folder_id=root_id,
                collection_id=db_root.collection.id,
                hash=child.hash,
            )
            mapping.append(EDocumentIntake.create(db_child.id, child))
            register_event(db, db_child, db_root.collection.owner, EventTypes.Create)
            parent.documents.append(db_child)
            db.add(db_child)
    db.commit()
    return mapping

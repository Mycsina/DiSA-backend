import os
from datetime import datetime

from sqlmodel import Session

from models.collection import Document, DocumentIntake
from models.folder import Folder, FolderIntake
from models.user import User
from storage.main import add_and_refresh

from uuid import UUID


def walk_folder(root: str, user: User) -> FolderIntake:
    """Walk through the given root path and create a tree of FolderIntake and DocumentIntake objects."""
    root_name = os.path.basename(root)
    root_folder = FolderIntake(name=root_name, owner=user, parent=None)
    folders_to_visit: list[str] = [root]
    parents_of_folders_to_visit: list[FolderIntake] = [root_folder]
    while len(folders_to_visit) > 0:
        folder = folders_to_visit.pop()
        parent = parents_of_folders_to_visit.pop()
        children = []
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            if os.path.isdir(item_path):
                children.append(FolderIntake(name=item, owner=user, parent=parent))
                folders_to_visit.append(item_path)
                parents_of_folders_to_visit.append(children[-1])
            else:
                children.append(
                    DocumentIntake(
                        name=item,
                        size=os.path.getsize(item_path),
                        content=open(item_path, "rb").read(),
                        parent_folder=parent,
                        submission_date=datetime.now(),
                    )
                )
        parent.children = children
    return root_folder


def create_folder(db: Session, root: FolderIntake, collection_id: UUID):
    """Creates Folder and Document structures in the database from the given root folder."""
    db_root = Folder(name=root.name, owner_id=root.owner.id)
    add_and_refresh(db, db_root)
    root_id = db_root.id
    if root_id is None:
        raise ValueError("Could not create root folder")
    children = root.children
    while len(children) > 0:
        child = children.pop()
        if isinstance(child, FolderIntake):
            db_child = Folder(name=child.name, owner_id=child.owner.id, parent_id=root_id)
            db.add(db_child)
            children.extend(child.children)
        else:
            db_child = Document(
                name=child.name,
                size=child.size,
                submission_date=child.submission_date,
                folder_id=root_id,
                collection_id=collection_id,
            )
            db.add(db_child)
    db.commit()

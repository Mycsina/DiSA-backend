import os
from datetime import datetime

from sqlmodel import Session

from models.collection import Document, DocumentIntake
from models.folder import Folder, FolderIntake
from models.user import User
from models.event import Event, EventTypes


def recreate_structure(db: Session, root: Folder) -> FolderIntake:
    """Recreate the FolderIntake structure from the structure in the database."""
    root_folder = FolderIntake(name=root.name)
    for child in root.sub_folders:
        root_folder.children.append(recreate_structure(db, child))
    for doc in root.documents:
        root_folder.children.append(doc)
    return root_folder


def walk_folder(root: str, user: User) -> FolderIntake:
    """Walk through the given root path and create a tree of FolderIntake and DocumentIntake objects."""
    root_name = os.path.basename(root)
    root_folder = FolderIntake(name=root_name)
    folders_to_visit: list[str] = [root]
    parents_of_folders_to_visit: list[FolderIntake] = [root_folder]
    while len(folders_to_visit) > 0:
        folder = folders_to_visit.pop()
        parent = parents_of_folders_to_visit.pop()
        children = []
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            if os.path.isdir(item_path):
                children.append(FolderIntake(name=item, parent=parent))
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


def create_folder(db: Session, root: FolderIntake, db_root: Folder) -> Folder:
    """Creates Folder and Document structures in the database from the given root folder."""
    print(db_root.collection)
    root_id = db_root.id
    if root_id is None:
        raise ValueError("Could not create root folder")
    children = root.children
    parents = [db_root] * len(children)
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
                submission_date=child.submission_date,
                folder_id=root_id,
                collection_id=db_root.collection.id,
            )
            db_child.events.append(
                Event(type=EventTypes.Create, user_id=db_root.collection.owner.id, document_id=db_child.id)
            )
            parent.documents.append(db_child)
            db.add(db_child)
    db.commit()
    return db_root

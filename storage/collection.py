from typing import List, Optional
from uuid import UUID

import storage.models as models
from sqlalchemy.orm import Session

import classes.collection as schema
from classes.user import User


def get_collections(db: Session) -> List[models.Collection]:
    return db.query(models.Collection).all()


def get_collection_by_id(db: Session, col_id: UUID) -> Optional[models.Collection]:
    return db.query(models.Collection).filter(models.Collection.id == col_id).first()


def create_collection(db: Session, name: str, data: bytes, user: User) -> models.Collection:
    user_id = user.id
    if name.split(".")[-1] == ["zip", "tar", "gz", "rar", "7z"]:
        # We're dealing with a zipped folder
        # TODO - implement this function
        pass
    else:
        # We're dealing with a single document
        document = schema.Document(name, data)

        collection = schema.Collection(name, user_id, [document])
        folder = models.Folder(name="root", parent_id=None)
        collection = models.Collection(
            name=collection.name,
            owner=collection.owner,
            root=folder.id,
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)
        return collection


# TODO - implement this function
def update_document(col_id: UUID, doc_id: UUID, file: bytes):
    collection = get_collection_by_id(col_id)
    pass


# TODO - implement this function
def delete_document(db: Session, col_id: UUID, doc_id: UUID):
    collection = get_collection_by_id(db, col_id)
    pass


def delete_collection(db: Session, col_id: UUID):
    db.query(models.Collection).filter(models.Collection.id == col_id).delete()
    db.commit()
    return True

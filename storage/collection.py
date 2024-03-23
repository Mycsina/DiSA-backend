import io
from typing import List, Optional
from uuid import UUID
import zipfile

import storage.models as models
from sqlalchemy.orm import Session

import classes.collection as schema
from classes.user import User
from models import Collection, Document, Folder

def get_collections(db: Session) -> List[models.Collection]:
    return db.query(models.Collection).all()


def get_collection_by_id(db: Session, col_id: UUID) -> Optional[models.Collection]:
    return db.query(models.Collection).filter(models.Collection.id == col_id).first()

def get_document_by_id(db: Session, doc_id: UUID) -> Optional[models.Document]:
    return db.query(models.Document).filter(models.Document.id == doc_id).first()


def create_collection(db: Session, name: str, data: bytes, user: User) -> models.Collection:
    user_id = user.id
    root_folder = Folder(name="root", parent_id=None)
    db.add(root_folder)
    db.commit()
    db.refresh(root_folder)
    docs = []
    if name.split(".")[-1].lower() in ["zip", "tar", "gz", "rar", "7z"]:
        # We're dealing with a zipped folder
        with zipfile.ZipFile(io.BytesIO(data)) as zip:
            for file_name in zip.namelist():
                with zip.open(file_name) as file:
                    doc = Document(name, data=file.read()) 
                    doc.folder_id = root_folder.id
                    docs.append(doc)
    else:
        # We're dealing with a single document
        doc = Document(name, data)
        doc.folder_id = root_folder.id
        docs.append(doc)

    for d in docs:
        db.add(d)
    collection = Collection(name, owner_id=user_id, root=root_folder.id)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def update_document(db: Session, col_id: UUID, doc_id: UUID, file: bytes):
    collection = get_collection_by_id(db, col_id)
    if collection is None:
        raise ValueError("Collection not found")
    document = get_document_by_id(db, doc_id)
    if document is None:
        raise ValueError("Document not found")
    if document.folder.collection_id != col_id:
        raise ValueError("Document not in the specified collection")
    
    document.data = file
    db.commit()
    return document


def delete_document(db: Session, col_id: UUID, doc_id: UUID):
    collection = get_collection_by_id(db, col_id)
    if collection is None:
        raise ValueError("Collection not found")
    document = get_document_by_id(db, doc_id)
    if document is None:
        raise ValueError("Document not found")
    if document.folder.collection_id != col_id: 
        raise ValueError("Document not in the specified collection")
    
    db.query(models.Document).filter(models.Document.id == doc_id).delete()
    db.commit()
    return True


def delete_collection(db: Session, col_id: UUID):
    collection = db.get_collection_by_id(col_id)
    if collection is None:
        raise ValueError("Collection not found")
    db.query(models.Collection).filter(models.Collection.id == col_id).delete()
    db.commit()
    return True

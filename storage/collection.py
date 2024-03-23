from typing import List, Optional
from uuid import UUID

from classes.collection import Document, Collection
from classes.event import Delete, Update
from classes.user import User


_COLLECTION_STORE: List[Collection] = []


def add_collection(collection):
    _COLLECTION_STORE.append(collection)


def get_collections() -> List[Collection]:
    return _COLLECTION_STORE


def get_collection_by_id(col_id: UUID) -> Optional[Collection]:
    for col in _COLLECTION_STORE:
        if col.id == col_id:
            return col


def create_collection(name: str, data: bytes, user: User):
    user_id = user.id
    if name.split(".")[-1] == ["zip", "tar", "gz", "rar", "7z"]:
        # We're dealing with a zipped folder
        # TODO - implement this function
        pass
    else:
        # We're dealing with a single document
        document = Document(name, data)

        collection = Collection(name, user_id, [document])
        add_collection(collection)


def update_document(collection_id: UUID, doc_id: UUID, file):
    for col in _COLLECTION_STORE:
        if col.id == collection_id:
            for doc in col.documents:
                if doc.id == doc_id:
                    doc.name = file.filename
                    doc.data = file.read()
                    doc.history.append(Update(doc.owner))


def delete_collection(collection_id: UUID):
    for i, col in enumerate(_COLLECTION_STORE):
        if col.id == collection_id:
            col = col.history.append(Delete(col.owner))

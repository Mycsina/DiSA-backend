from typing import List, Optional
from uuid import UUID

from classes.collection import Document, Collection
from classes.event import Delete


_COLLECTION_STORE: List[Collection] = []


def add_collection(collection):
    _COLLECTION_STORE.append(collection)


def get_collections() -> List[Collection]:
    return _COLLECTION_STORE


def get_collection_by_id(doc_id: UUID) -> Optional[Collection]:
    for doc in _COLLECTION_STORE:
        if doc.id == doc_id:
            return doc


def create_collection(name: str, data: bytes, user_id: UUID):
    if name.split(".")[-1] == ["zip", "tar", "gz", "rar", "7z"]:
        # We're dealing with a zipped folder
        # TODO - implement this function
        pass
    else:
        # We're dealing with a single document
        document = Document(name, data)

        collection = Collection(name, user_id, [document])
        add_collection(collection)


# TODO - implement this function
def update_collection(collection_id: UUID, file):
    pass


def delete_collection(collection_id: UUID):
    for i, col in enumerate(_COLLECTION_STORE):
        if col.id == collection_id:
            col = col.history.append(Delete(col.owner))

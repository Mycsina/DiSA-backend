from sqlmodel import Session

from models.collection import Collection, Document
from models.event import CollectionEvent, DocumentEvent, EventTypes
from models.user import User


def register_event(db: Session, col_or_doc: Collection | Document, user: User, event_type: EventTypes):
    if col_or_doc.id is None:
        raise ValueError("Collection or Document must have an ID to register an event. This should never happen.")
    if user.id is None:
        raise ValueError("User must have an ID to register an event. This should never happen.")
    if isinstance(col_or_doc, Collection):
        event = CollectionEvent(user_id=user.id, type=event_type, collection_id=col_or_doc.id)
    else:
        event = DocumentEvent(user_id=user.id, type=event_type, document_id=col_or_doc.id)
    db.add(event)
    db.commit()
    return True

import logging
from sqlmodel import Session

from models.collection import Collection, Document
from models.event import CollectionEvent, DocumentEvent, EventTypes
from models.user import User

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def register_event(db: Session, col_or_doc: Collection | Document, user: User, event_type: EventTypes):
    logger.debug(f"Registering event of type '{event_type}' for {'Collection' if isinstance(col_or_doc, Collection) else 'Document'} by user {user.id}")
    if col_or_doc.id is None:
        logger.error("Collection or Document must have an ID to register an event.")
        raise ValueError("Collection or Document must have an ID to register an event. This should never happen.")
    if user.id is None:
        logger.error("User must have an ID to register an event.")
        raise ValueError("User must have an ID to register an event. This should never happen.")
    if isinstance(col_or_doc, Collection):
        event = CollectionEvent(user_id=user.id, type=event_type, collection_id=col_or_doc.id)
    else:
        event = DocumentEvent(user_id=user.id, type=event_type, document_id=col_or_doc.id)
    db.add(event)
    logger.info(f"Event of type '{event_type}' registered successfully for {'Collection' if isinstance(col_or_doc, Collection) else 'Document'} with ID '{col_or_doc.id}' by user '{user.id}'.")
    return True

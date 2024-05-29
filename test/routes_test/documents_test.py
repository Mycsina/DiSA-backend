from unittest import mock
from uuid import uuid4
import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from unittest.mock import MagicMock, Mock, patch

import routes.users as users
import routes.collections as collections
import routes.documents as documents
from utils.security import get_current_user
from utils.exceptions import IntegrityBreach
from models.user import UserCreate
from models.folder import FolderIntake
from models.collection import (
    Collection,
    Document,
    Permission,
)

# Set up the database URL to point to your test database
SQLALCHEMY_DATABASE_URL = "../test.db" # or "sqlite:///../test.db" ?
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create a FastAPI app for testing
app = FastAPI()
app.include_router(users.users_router)
app.include_router(collections.collections_router)
app.include_router(documents.documents_router)

# Create a dependency override to use the test database
def get_test_db():
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        db = TestSessionLocal()
        yield db
    finally:
        db.close()

# Dependency override
app.dependency_overrides[get_current_user] = get_test_db

# Ensure the test database tables are created
SQLModel.metadata.create_all(bind=engine)

# Create a test user
@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Mock the get_current_user dependency
@pytest.fixture
def current_user():
    return UserCreate(id=uuid4(), email="test@example.com")



# Test update_document endpoint - success
@pytest.mark.asyncio
async def test_update_document_success(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.update_document") as mock_update_document:

        mock_get_collection_by_id.return_value = mock.Mock()
        mock_get_document_by_id.return_value = mock.Mock()
        mock_update_document.return_value = None

        files = {"file": ("testfile.txt", b"file content")}
        response = await client.put(f"/documents?col_uuid={uuid4()}&doc_uuid={uuid4()}", files=files)

        assert response.status_code == 200
        assert "Document updated successfully" in response.text
        assert '"update_uuid": "{}"'.format(str(uuid4())) in response.text

# Test update_document endpoint - error - collection not found
@pytest.mark.asyncio
async def test_update_document_error_collection_not_found(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id:
        mock_get_collection_by_id.return_value = None

        files = {"file": ("testfile.txt", b"file content")}
        response = await client.put(f"/documents?col_uuid={uuid4()}&doc_uuid={uuid4()}", files=files)

        assert response.status_code == 404
        assert "Collection not found" in response.text

# Test update_document endpoint - error - document not found
@pytest.mark.asyncio
async def test_update_document_error_not_found(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()
    upload_file = Mock(filename="testfile.txt", read=Mock(return_value=b"file content"))
    
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_get_collection_by_id.return_value = Mock()
        mock_get_document_by_id.return_value = None

        response = await client.put(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}", files={"file": upload_file})

        assert response.status_code == 404
        assert "Document not found" in response.text

# Test update_document endpoint - error - document not in the collection
@pytest.mark.asyncio
async def test_update_document_error_not_in_collection(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()
    upload_file = Mock(filename="testfile.txt", read=Mock(return_value=b"file content"))

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_collection = mock_get_collection_by_id.return_value
        mock_document = mock_get_document_by_id.return_value
        mock_collection.documents = []

        response = await client.put(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}", files={"file": upload_file})

        assert response.status_code == 404
        assert "Document not in the specified collection" in response.text

# Test update_document endpoint - error - no permission to write
@pytest.mark.asyncio
async def test_update_document_error_no_permission(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_collection = mock_get_collection_by_id.return_value
        mock_document = mock_get_document_by_id.return_value
        mock_collection.can_write.return_value = False

        files = {"file": ("testfile.txt", b"file content")}
        response = await client.put(f"/documents?col_uuid={uuid4()}&doc_uuid={uuid4()}", files=files)

        assert response.status_code == 403
        assert "You do not have permission to write to this collection" in response.text

# Test update_document endpoint - error - document update failed
@pytest.mark.asyncio
async def test_update_document_error_update_failed(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()
    upload_file = Mock(filename="testfile.txt", read=Mock(return_value=b"file content"))

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.update_document") as mock_update_document:

        mock_collection = mock_get_collection_by_id.return_value
        mock_document = mock_get_document_by_id.return_value
        mock_collection.documents = [mock_document]
        mock_collection.can_write.return_value = True
        mock_update_document.return_value = None
        mock_document.next = None

        response = await client.put(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}", files={"file": upload_file})

        assert response.status_code == 500
        assert "Document update failed" in response.text

# Test update_document endpoint - error - document integrity breach
@pytest.mark.asyncio
async def test_update_document_error_integrity_breach(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()
    upload_file = Mock(filename="testfile.txt", read=Mock(return_value=b"file content"))

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.update_document", side_effect=IntegrityBreach) as mock_update_document:

        mock_collection = mock_get_collection_by_id.return_value
        mock_document = mock_get_document_by_id.return_value
        mock_collection.documents = [mock_document]
        mock_collection.can_write.return_value = True

        response = await client.put(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}", files={"file": upload_file})

        assert response.status_code == 400
        assert "Document update failed. Verify the document hasn't already been updated" in response.text

# Test update_document endpoint - error - internal server error
@pytest.mark.asyncio
async def test_update_document_error_internal_server_error(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()
    upload_file = Mock(filename="testfile.txt", read=Mock(return_value=b"file content"))

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.update_document", side_effect=Exception) as mock_update_document:

        mock_collection = mock_get_collection_by_id.return_value
        mock_document = mock_get_document_by_id.return_value
        mock_collection.documents = [mock_document]
        mock_collection.can_write.return_value = True

        response = await client.put(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}", files={"file": upload_file})

        assert response.status_code == 500
        assert "Internal server error" in response.text




# Test delete_document endpoint - success
@pytest.mark.asyncio
async def test_delete_document_success(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.delete_document") as mock_delete_document, \
         patch("routes.documents.get_current_user", return_value=current_user):

        mock_collection = Mock()
        mock_document = Mock()
        mock_get_collection_by_id.return_value = mock_collection
        mock_get_document_by_id.return_value = mock_document

        mock_collection.documents = [mock_document]
        mock_collection.can_write.return_value = True

        response = await client.delete(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 200
        assert "Document deleted successfully" in response.text

        mock_delete_document.assert_called_once_with(Mock(), mock_document)

# Test delete_document endpoint - error - collection not foung
@pytest.mark.asyncio
async def test_delete_document_error_collection_not_found(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id:
        mock_get_collection_by_id.return_value = None

        response = await client.delete(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 404
        assert "Collection not found" in response.text

# Test delete_document endpoint - error - no permission to write
@pytest.mark.asyncio
async def test_delete_document_error_no_permission(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_collection = mock_get_collection_by_id.return_value
        mock_get_document_by_id.return_value = Mock()
        mock_collection.can_write.return_value = False

        response = await client.delete(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 403
        assert "You do not have permission to write to this collection" in response.text

# Test delete_document endpoint - error - document not found
@pytest.mark.asyncio
async def test_delete_document_error_not_found(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_get_collection_by_id.return_value = Mock()
        mock_get_document_by_id.return_value = None

        response = await client.delete(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 404
        assert "Document not found" in response.text

# Test delete_document endpoint - error - document not in the collection
@pytest.mark.asyncio
async def test_delete_document_error_not_in_collection(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_collection = mock_get_collection_by_id.return_value
        mock_document = mock_get_document_by_id.return_value
        mock_collection.documents = []

        response = await client.delete(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 404
        assert "Document not in the specified collection" in response.text

# Test delete_document endpoint - error - internal server error
@pytest.mark.asyncio
async def test_delete_document_error_internal_server_error(client, current_user):
    col_uuid = uuid4()
    doc_uuid = uuid4()

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.delete_document", side_effect=Exception("Unexpected error")) as mock_delete_document:

        mock_collection = mock_get_collection_by_id.return_value
        mock_document = mock_get_document_by_id.return_value
        mock_collection.documents = [mock_document]
        mock_collection.can_write.return_value = True

        response = await client.delete(f"/documents/?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 500
        assert "Internal server error" in response.text



# Test search_documents endpoint - success
@pytest.mark.asyncio
async def test_search_documents_success(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.search_documents") as mock_search_documents:

        mock_get_collection_by_id.return_value = mock.Mock()
        mock_search_documents.return_value = [{"name": "testdoc", "size": 1024}]

        response = await client.get(f"/documents/search?col_uuid={uuid4()}&name=testdoc")

        assert response.status_code == 200
        assert '[{"name": "testdoc", "size": 1024}]' in response.text

# Test search_documents endpoint - error - Collection not found
@pytest.mark.asyncio
async def test_search_documents_error_collection_not_found(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id:
        mock_get_collection_by_id.return_value = None

        response = await client.get(f"/documents/search?col_uuid={uuid4()}&name=testdoc")

        assert response.status_code == 404
        assert "Collection not found" in response.text

# Test search_documents endpoint - error - not the owner of collection
@pytest.mark.asyncio
async def test_search_documents_error_not_the_owner(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id:

        mock_collection = mock_get_collection_by_id.return_value
        mock_collection.owner = None

        response = await client.get(f"/documents/search?col_uuid={uuid4()}&name=testdoc")

        assert response.status_code == 403
        assert "You are not the owner of this Collection" in response.text

# Test search_documents endpoint - error - no documents found
@pytest.mark.asyncio
async def test_search_documents_error_no_documents_found(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.search_documents") as mock_search_documents:

        mock_get_collection_by_id.return_value = mock.Mock()
        mock_search_documents.return_value = None

        response = await client.get(f"/documents/search?col_uuid={uuid4()}&name=testdoc")

        assert response.status_code == 404
        assert "No documents found" in response.text

# Test search_documents endpoint - error - internal server error
@pytest.mark.asyncio
async def test_search_documents_error_internal_server_error(client, current_user):
    col_uuid = uuid4()
    name = "test_document"

    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.search_documents") as mock_search_documents, \
         patch("routes.documents.get_current_user", return_value=current_user):

        mock_collection = Mock()
        mock_get_collection_by_id.return_value = mock_collection
        mock_search_documents.side_effect = Exception("Something went wrong")

        response = await client.get(f"/documents/search?col_uuid={col_uuid}&name={name}")

        assert response.status_code == 500
        assert "Internal server error" in response.text

        mock_search_documents.assert_called_once_with(Mock(), mock_collection, name)



# Test get_document_history endpoint - success
@pytest.mark.asyncio
async def test_get_document_history_success(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.get_document_history") as mock_get_document_history:

        mock_get_collection_by_id.return_value = mock.Mock()
        mock_get_document_by_id.return_value = mock.Mock()
        mock_get_document_history.return_value = [{"version": 1, "changes": "Initial version"}]

        response = await client.get(f"/documents/history?col_uuid={uuid4()}&doc_uuid={uuid4()}")

        assert response.status_code == 200
        assert str(response.json()) == '[{"version": 1, "changes": "Initial version"}]'

# Test get_document_history endpoint - error - collection not found
@pytest.mark.asyncio
async def test_get_document_history_error_collection_not_found(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id:
        mock_get_collection_by_id.return_value = None

        response = await client.get(f"/documents/history?col_uuid={uuid4()}&doc_uuid={uuid4()}")

        assert response.status_code == 404
        assert "Collection not found" in response.text

# Test get_document_history endpoint - error - no permission to read
@pytest.mark.asyncio
async def test_get_document_history_error_no_permission(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_collection = mock_get_collection_by_id.return_value
        mock_collection.can_read.return_value = False
        mock_get_document_by_id.return_value = mock.Mock()

        response = await client.get(f"/documents/history?col_uuid={uuid4()}&doc_uuid={uuid4()}")

        assert response.status_code == 403
        assert "You do not have permission to read this collection" in response.text

# Test get_document_history endpoint - error - document not found
@pytest.mark.asyncio
async def test_get_document_history_error_document_not_found(client, current_user):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:

        mock_get_collection_by_id.return_value = mock.Mock()
        mock_get_document_by_id.return_value = None

        response = await client.get(f"/documents/history?col_uuid={uuid4()}&doc_uuid={uuid4()}")

        assert response.status_code == 404
        assert "Document not found" in response.text

# Test get_document_history endpoint - error - document not in collection
@pytest.mark.asyncio
async def test_get_document_history_error_document_not_in_collection(client, current_user, col_uuid, doc_uuid):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.get_document_history") as mock_get_document_history:

        mock_get_collection_by_id.return_value = Mock(can_read=Mock(return_value=True), documents=[])
        mock_get_document_by_id.return_value = Mock()
        mock_get_document_history.return_value = ["history_entry_1", "history_entry_2"]

        response = await client.get(f"/documents/history?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 404
        assert "Document not in the specified collection" in response.text

# Test get_document_history endpoint - error - internal server error
@pytest.mark.asyncio
async def test_get_document_history_error_internal_server_error(client, current_user, col_uuid, doc_uuid):
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id, \
         patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id, \
         patch("routes.documents.collections.get_document_history") as mock_get_document_history:

        mock_get_collection_by_id.side_effect = Exception("Something went wrong")

        response = await client.get(f"/documents/history?col_uuid={col_uuid}&doc_uuid={doc_uuid}")

        assert response.status_code == 500
        assert "Internal server error" in response.text

        mock_get_document_history.assert_not_called()

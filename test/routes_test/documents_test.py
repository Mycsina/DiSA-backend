import os
from tempfile import NamedTemporaryFile
import uuid
from unittest.mock import ANY, AsyncMock, patch, MagicMock
import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine

from models.user import User, UserRole
import routes.documents as documents
import routes.collections as collections
import test.routes_test.collections_test as collections_test
from utils.security import get_current_user

# Set up the database URL to point to your test database
SQLALCHEMY_DATABASE_URL = "sqlite:///../test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create a FastAPI app for testing
app = FastAPI()
app.include_router(documents.documents_router)
app.include_router(collections.collections_router)

# Create a dependency override to use the test database
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_test_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create a temporary file
@pytest.fixture(scope="module")
def temp_file():
    with NamedTemporaryFile(delete=False) as temp:
        temp.write(b"This is a test file")
        temp.flush()
        yield temp.name
    os.unlink(temp.name)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

# Dependency override
app.dependency_overrides[get_current_user] = get_test_db

# Ensure the test database tables are created
SQLModel.metadata.create_all(bind=engine)

# Helper function to create a mock user
def create_mock_user():
    return User(
        id=uuid.uuid4(),
        name="test_user",
        email="test_user@example.com",
        nic="123456789",
        password="password",
        role=UserRole.USER
    )



# Test update_document endpoint
@pytest.mark.asyncio
async def test_update_document(temp_file, client):
    # Create a collection first
    collection_info = await collections_test.test_create_collection(temp_file, client)
    col_uuid = collection_info["uuid"]
    print(f"Collection info: {collection_info}")

    # Create a document associated with the collection
    with patch("routes.documents.collections.get_collection_by_id") as mock_get_collection_by_id:
        mock_get_collection_by_id.return_value = MagicMock()
        mock_get_collection_by_id.return_value.id = col_uuid

        with patch("routes.documents.collections.create_document") as mock_create_document:
            mock_create_document.return_value = MagicMock()
            mock_create_document.return_value.id = uuid.uuid4()  # Simulate the creation of a new document

            doc_uuid = mock_create_document.return_value.id

            # Proceed with the update test
            async with AsyncClient(app=app, base_url="http://test") as client:
                with patch("routes.documents.collections.get_document_by_id") as mock_get_document_by_id:
                    mock_get_document_by_id.return_value = MagicMock()
                    mock_get_document_by_id.return_value.next = MagicMock()

                    # Call the update endpoint with the created document
                    response = await client.put(
                        "/documents/",
                        params={"col_uuid": str(col_uuid), "doc_uuid": str(doc_uuid)},
                        files={"file": ("filename.txt", open(temp_file, "rb"), "text/plain")}
                    )

                    # Check the response status code
                    assert response.status_code == 200

                    # Check if the response contains the expected message
                    expected_message = "Document updated successfully"
                    assert response.json()["message"] == expected_message

                    # Check if the response contains the UUID of the updated document
                    assert "update_uuid" in response.json()
                    assert isinstance(response.json()["update_uuid"], str)


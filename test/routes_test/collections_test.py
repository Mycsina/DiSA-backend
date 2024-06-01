from datetime import datetime
from tempfile import NamedTemporaryFile
import uuid
import os
from unittest.mock import MagicMock, Mock, patch

from models.folder import Folder, FolderIntake
from models.user import User, UserRole
import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from sqlalchemy.sql.expression import func

import routes.collections as collections
import routes.documents as documents
import routes.users as users
import test.routes_test.users_test as users_test
from utils.security import get_current_user
from models.collection import Collection, CollectionInfo, Permission


# Set up the database URL to point to your test database
SQLALCHEMY_DATABASE_URL = "sqlite:///../test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create a FastAPI app for testing
app = FastAPI()
app.include_router(users.users_router)
app.include_router(collections.collections_router)
app.include_router(documents.documents_router)


# Create a dependency override to use the test database
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_test_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency override
app.dependency_overrides[get_current_user] = get_test_db

# Ensure the test database tables are created
SQLModel.metadata.create_all(bind=engine)

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


# Test create_collection endpoint
@patch("routes.collections.get_current_user", MagicMock(return_value=Mock()))
@pytest.mark.asyncio
async def test_create_collection(temp_file, client):
    with patch("routes.collections.collections.create_collection") as mock_create_collection:
        mock_create_collection.return_value = Mock(id="550e8400e29b41d4a716446655440000")

        transaction_address = "0x123abc"

        with open(temp_file, "rb") as f:
            response = client.post(
                "/collections/",
                data={"transaction_address": transaction_address},
                files={"file": f}
            )
        assert response.status_code == 200

        collection_info = response.json()            
        assert collection_info["message"] == "Collection created successfully"
        assert "uuid" in collection_info

    return collection_info
        


# Test download_collection endpoint
@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.users.get_user_by_email")
@pytest.mark.asyncio
async def test_download_collection(mock_get_user_by_email, mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    collection = Collection(id=1, name="Test Collection", owner_id=1)

    collection.folder = Folder(id=1, name="TestFolder", collection_id=1)

    mock_get_user_by_email.return_value = user
    mock_get_collection_by_id.return_value = collection

    response = client.get(
        "/collections/download",
        params={"col_uuid": "550e8400e29b41d4a716446655440000", "email": "example@email.com"},
    )

    assert response.status_code == 200



# Test get_all_collections endpoint
@patch("routes.collections.collections.get_collections")
@pytest.mark.asyncio
async def test_get_all_collections(mock_get_collections, client):
    mock_collections = [
        Collection(name="Collection 1", owner_id="test_owner_id"),
        Collection(name="Collection 2", owner_id="test_owner_id"),
        Collection(name="Collection 3", owner_id="test_owner_id"),
    ]
    mock_get_collections.return_value = mock_collections

    register_response = await users_test.test_register_user()
    user_token = register_response.json()['token']

    response = client.get(
        "/collections/",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 200
    collections_list = response.json()
    assert len(collections_list) == len(mock_collections)




# Test get_user_collections endpoint
@patch("routes.collections.get_current_user")
@patch("routes.collections.collections.get_collections_by_user")
@pytest.mark.asyncio
async def test_get_user_collections(mock_get_collections_by_user, mock_get_current_user, client):
    
    userId = uuid.uuid4()
    user_token = "test_token"

    mock_get_current_user.return_value = User(id=userId, name="test_user", email="example@email.com", role=UserRole.USER)

    mock_collections = [
        Collection(name="Collection 1", owner_id=userId),
        Collection(name="Collection 2", owner_id=userId),
        Collection(name="Collection 3", owner_id=userId),
    ]
    mock_get_collections_by_user.return_value = mock_collections

    response = client.get(
        "/collections/user",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 200
    collections_list = response.json()
    assert len(collections_list) == len(mock_collections)



@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.users.get_user_by_email")
@pytest.mark.asyncio
async def test_get_shared_collection(mock_get_user_by_email, mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    collection = Collection(id=1, name="Test Collection", owner_id=1)

    collection.folder = Folder(id=1, name="TestFolder", collection_id=1)

    mock_get_user_by_email.return_value = user
    mock_get_collection_by_id.return_value = collection
    
    response = client.get(
        "/shared",
        params={"col_uuid": "550e8400e29b41d4a716446655440000", "email": "example@email.com"},
    )

    assert response.status_code == 200

    

# Test get_collection_hierarchy endpoint
@patch("routes.collections.collections.get_collection_hierarchy")
@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.get_current_user")
@pytest.mark.asyncio
async def test_get_collection_hierarchy(mock_get_current_user, mock_get_collection_by_id, mock_get_collection_hierarchy, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    mock_get_current_user.return_value = user

    collection = Collection(id="550e8400e29b41d4a716446655440000", name="Test Collection", owner_id=1)
    hierarchy = FolderIntake(id=1, name="RootFolder", collection_id=collection.id)
    
    mock_get_collection_by_id.return_value = collection
    mock_get_collection_hierarchy.return_value = hierarchy

    col_uuid = "550e8400e29b41d4a716446655440000"
    response = client.get(
        f"/hierarchy",
        params={"col_uuid": col_uuid}
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == 1
    assert response_data["name"] == "RootFolder"
    assert response_data["collection_id"] == collection.id
    


# Test delete_collection endpoint
@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.get_current_user")
@pytest.mark.asyncio
async def test_delete_collection(mock_get_current_user, mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    mock_get_current_user.return_value = user

    collection = Collection(id="550e8400e29b41d4a716446655440000", name="Test Collection", owner_id=1)
    mock_get_collection_by_id.return_value = collection

    col_uuid = "550e8400e29b41d4a716446655440000"
    response = client.delete(
        f"/?col_uuid={col_uuid}"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"message": "Collection deleted successfully"}



# Test add_permission endpoint
@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.get_current_user")
@patch("routes.collections.users.get_user_by_email")
@patch("routes.collections.users.create_anonymous_user")
@pytest.mark.asyncio
async def test_add_permission(mock_create_anonymous_user, mock_get_user_by_email, mock_get_current_user, mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    mock_get_current_user.return_value = user

    collection = Collection(id="550e8400e29b41d4a716446655440000", name="Test Collection", owner_id=1)
    mock_get_collection_by_id.return_value = collection

    db_user = User(id=2, name="another_user", email="another@example.com", role=UserRole.USER)
    mock_get_user_by_email.return_value = db_user

    mock_create_anonymous_user.return_value = db_user

    col_uuid = "550e8400e29b41d4a716446655440000"
    permission = Permission.write
    email = "another@example.com"
    response = client.post(
        f"/permissions?col_uuid={col_uuid}&permission={permission}&email={email}"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"message": "Permission added successfully"}



# Test get_permissions endpoint
@patch("routes.collections.collections.get_collection_by_id")
@pytest.mark.asyncio
def test_get_permissions(mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    col_uuid = uuid.UUID("550e8400e29b41d4a716446655440001")
    permissions = [
        {"id": 2, "collection_id": col_uuid, "user_id": user.id},
        {"id": 3, "collection_id": col_uuid, "user_id": 3} 
    ]

    response = client.get(f"/permissions?col_uuid={col_uuid}")
    assert response.status_code == 200

    response_data = response.json()
    assert response_data == permissions



# Test remove_permission endpoint
@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.get_current_user")
@patch("routes.collections.users.get_user_by_email")
@pytest.mark.asyncio
async def test_remove_permission(mock_get_user_by_email, mock_get_current_user, mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    mock_get_current_user.return_value = user

    collection = Collection(id="550e8400e29b41d4a716446655440000", name="Test Collection", owner_id=1)
    mock_get_collection_by_id.return_value = collection

    db_user = User(id=2, name="another_user", email="example2@email.com", role=UserRole.USER)
    mock_get_user_by_email.return_value = db_user

    col_uuid = "550e8400e29b41d4a716446655440000"
    email = "example@email.com"
    response = client.delete(
        f"/permissions?col_uuid={col_uuid}&email={email}"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"message": "Permission removed successfully"}



# Test get_filter_documents endpoint
@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.get_current_user")
@pytest.mark.asyncio
async def test_get_filter_documents(mock_get_current_user, mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    mock_get_current_user.return_value = user

    collection = Collection(id="550e8400e29b41d4a716446655440000", name="Test Collection", owner_id=1)
    mock_get_collection_by_id.return_value = collection

    col_uuid = "550e8400e29b41d4a716446655440000"
    response = client.get(
        f"/documents/filter?col_uuid={col_uuid}"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"message": "Documents filtered successfully"}
    assert "documents" in response_data



# Test update_collection_name endpoint
@patch("routes.collections.collections.get_collection_by_id")
@patch("routes.collections.get_current_user")
@pytest.mark.asyncio
async def test_update_collection_name(mock_get_current_user, mock_get_collection_by_id, client):
    user = User(id=1, name="test_user", email="example@email.com", role=UserRole.USER)
    mock_get_current_user.return_value = user

    collection = Collection(id="550e8400e29b41d4a716446655440000", name="Test Collection", owner_id=1)
    mock_get_collection_by_id.return_value = collection

    col_uuid = "550e8400e29b41d4a716446655440000"
    new_name = "New Collection Name"
    response = client.put(
        f"/name?col_uuid={col_uuid}&name={new_name}"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data == {"message": "Collection name updated successfully"}
    assert collection.name == new_name

    
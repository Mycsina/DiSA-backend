from datetime import datetime
from tempfile import NamedTemporaryFile
import uuid
import os
from unittest.mock import MagicMock, Mock, patch

from models.folder import Folder
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
from models.collection import Collection, CollectionInfo


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

        print("Response: ", response.json())
        return response
        


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

    print("Response 3: ", response)

    assert response.status_code == 200



# Test get_all_collections endpoint - success
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
    # Prepare mock data
    user = User(id="150e8400e29b41d4a716446655440001", name="test_user", email="test@example.com", role=UserRole.USER)
    collections = [
        CollectionInfo(
            id="550e8400e29b41d4a716446655440001",
            name="Collection 1",
            owner_id="150e8400e29b41d4a716446655440001",
            documents=[],
            events=[],
            created=datetime.now(),
            last_access=datetime.now()
        ),
        CollectionInfo(
            id="550e8400e29b41d4a716446655439002",
            name="Collection 2",
            owner_id="150e8400e29b41d4a716446655440001",
            documents=[],
            events=[], 
            created=datetime.now(),  
            last_access=datetime.now() 
        ),
    ]

    mock_get_current_user.return_value = user
    mock_get_collections_by_user.return_value = collections

    response = client.get("/collections")

    assert response.status_code == 200
    assert len(response.json()) == 2



# Test get_shared_collection endpoint
@patch("routes.collections.users.get_user_by_email")
@patch("routes.collections.collections.get_collection_by_id")
@pytest.mark.asyncio
async def test_get_shared_collection(mock_get_user_by_email, mock_get_collection_by_id, client):
    # Define mock data
    email = "test@example.com"
    col_uuid = uuid.UUID("550e8400e29b41d4a716446655440001")
    db_user = {"id": 1, "email": email}  # Mocked user data
    col_info = {
        "id": str(col_uuid),
        "name": "Test Collection",
        "owner_id": 1,
        "documents": [],
        "events": [],
        "created": datetime.now().isoformat(),
        "last_access": datetime.now().isoformat()
    }

    # Mock the functions
    mock_get_user_by_email.return_value = db_user
    mock_get_collection_by_id.return_value = col_info

    # Make request to the endpoint
    response = client.get(
        f"/collections/shared?col_uuid={col_uuid}&email={email}"
    )

    # Assert response status code is 200
    assert response.status_code == 200

    # Assert response data matches the expected collection info
    assert response.json() == col_info

    # Verify that the mocked functions were called
    users.get_user_by_email.assert_called_once_with(mock_get_user_by_email.ANY, email)
    collections.get_collection_by_id.assert_called_once_with(mock_get_collection_by_id.ANY, col_uuid, db_user)







# # Test get_shared_collection endpoint - success
# @pytest.mark.asyncio
# async def test_get_shared_collection_success(client, get_test_db):
#     from models.collection import Collection
#     from models.user import UserCreate
#     from storage.user import create_user

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Create a shared UUID for the collection
#         shared_uuid = uuid.uuid4()

#         # Create a shared link for the collection with an email
#         shared_link = f"/collections/shared?col_uuid={test_collection.id}&email=test@example.com"

#     # Send a GET request to fetch the shared collection information
#     response = await client.get(shared_link)
#     assert response.status_code == 200

#     collection_info = response.json()
#     assert collection_info["name"] == "Test Collection"
#     assert collection_info["owner_id"] == db_user.id

# # Test get_collection_hierarchy endpoint - success
# @pytest.mark.asyncio
# async def test_get_collection_hierarchy_success(client, get_test_db):
#     from models.collection import Collection, FolderIntake
#     from models.user import UserCreate
#     from storage.user import create_user

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Create a hierarchy of folders for the collection
#         root_folder = FolderIntake(name="Root", collection_id=test_collection.id)
#         db.add(root_folder)
#         db.commit()

#         subfolder1 = FolderIntake(name="Subfolder1", collection_id=test_collection.id, parent_id=root_folder.id)
#         db.add(subfolder1)
#         db.commit()

#         subfolder2 = FolderIntake(name="Subfolder2", collection_id=test_collection.id, parent_id=root_folder.id)
#         db.add(subfolder2)
#         db.commit()

#         # Send a GET request to fetch the collection hierarchy
#         response = await client.get(f"/collections/hierarchy?col_uuid={test_collection.id}")

#     assert response.status_code == 200

#     folder_hierarchy = response.json()
#     assert folder_hierarchy["name"] == "Root"
#     assert len(folder_hierarchy["children"]) == 2




# # Test delete_collection endpoint - success
# @pytest.mark.asyncio
# async def test_delete_collection_success(client, get_test_db):
#     from models.collection import Collection
#     from models.user import UserCreate
#     from storage.user import create_user

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Send a DELETE request to delete the collection
#         response = await client.delete(f"/collections/?col_uuid={test_collection.id}")
#         assert response.status_code == 200
#         assert response.json()["message"] == "Collection deleted successfully"

#         deleted_collection = db.get(Collection, test_collection.id)
#         assert deleted_collection is None




# # Test add_permission endpoint - success
# @pytest.mark.asyncio
# async def test_add_permission_success(client, get_test_db):
#     from models.collection import Collection, Permission
#     from models.user import UserCreate
#     from storage.user import create_user

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Define test permission
#         test_permission = Permission(read=True, write=True)

#         # Add permission for the test user
#         test_data = {"col_uuid": test_collection.id, "permission": test_permission.dict(), "email": "test@example.com"}
#         response = await client.post("/collections/permissions", json=test_data)
#         assert response.status_code == 200
#         assert response.json()["message"] == "Permission added successfully"



# # Test get_permissions endpoint - success
# @pytest.mark.asyncio
# async def test_get_permissions_success(client, get_test_db):
#     from models.collection import Collection, Permission
#     from models.user import UserCreate
#     from storage.user import create_user

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Add permission for the test user to the test collection
#         test_permission = Permission(read=True, write=True)
#         collections.add_permission(db, test_collection, db_user, test_permission, db_user)
#         db.commit()

#         # Send a GET request to retrieve permissions
#         response = await client.get(f"/collections/permissions?col_uuid={test_collection.id}")
#         assert response.status_code == 200

#         permissions = response.json()
#         assert isinstance(permissions, list)
#         assert len(permissions) == 1  # Assuming only one permission is added ?
#         assert permissions[0]["email"] == "test@example.com"
#         assert permissions[0]["read"] == True
#         assert permissions[0]["write"] == True



# # Test remove_permission endpoint - success
# @pytest.mark.asyncio
# async def test_remove_permission_success(client, get_test_db):
#     from models.collection import Collection, Permission
#     from models.user import UserCreate
#     from storage.user import create_user

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Add permission for the test user to the test collection
#         test_permission = Permission(read=True, write=True)
#         collections.add_permission(db, test_collection, db_user, test_permission, db_user)
#         db.commit()

#         # Send a DELETE request to remove permission
#         response = await client.delete(
#             f"/collections/permissions?col_uuid={test_collection.id}&email=test@example.com",
#             json=test_permission.dict(),
#         )
#         assert response.status_code == 200
#         assert response.json() == {"message": "Permission removed successfully"}


# # Test filter_documents endpoint - success
# @pytest.mark.asyncio
# async def test_filter_documents_success(client, get_test_db):
#     from models.collection import Collection, Document
#     from models.user import UserCreate
#     from storage.user import create_user

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Create some test documents for the collection
#         test_documents = [
#             Document(name=f"Document{i}.txt", size=1024 * i, owner_id=db_user.id, collection_id=test_collection.id)
#             for i in range(1, 4)
#         ]
#         db.add_all(test_documents)
#         db.commit()

#         # Send a GET request to filter documents by name
#         response_name_filter = await client.get(f"/collections/{test_collection.id}/filter?name=Document1.txt")
#         assert response_name_filter.status_code == 200
#         assert len(response_name_filter.json()) == 1
#         assert response_name_filter.json()[0]["name"] == "Document1.txt"

#         # Send a GET request to filter documents by max_size
#         response_max_size_filter = await client.get(f"/collections/{test_collection.id}/filter?max_size=2048")
#         assert response_max_size_filter.status_code == 200
#         assert len(response_max_size_filter.json()) == 2
#         assert all(doc["size"] <= 2048 for doc in response_max_size_filter.json())

#         # Send a GET request to filter documents by last_access
#         response_last_access_filter = await client.get(
#             f"/collections/{test_collection.id}/filter?last_access=2024-05-30T12:00:00"
#         )
#         assert response_last_access_filter.status_code == 200
#         assert len(response_last_access_filter.json()) == 3



# # Test update_collection_name endpoint - success
# @pytest.mark.asyncio
# async def test_update_collection_name_success(client, get_test_db):
#     from models.collection import Collection
#     from models.user import UserCreate
#     from storage.user import create_user
#     from storage.collection import get_collection_by_id

#     # Create a test user
#     async with get_test_db() as db:
#         test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
#         db_user = create_user(db, user=test_user)
#         db.commit()

#         # Create a test collection associated with the user
#         test_collection = Collection(name="Test Collection", owner_id=db_user.id)
#         db.add(test_collection)
#         db.commit()

#         # Send a PUT request to update the collection name
#         updated_name = "Updated Collection Name"
#         response = await client.put(f"/collections/name?col_uuid={test_collection.id}&name={updated_name}")
#         assert response.status_code == 200
#         assert response.json()["message"] == "Collection name updated successfully"

#         async with get_test_db() as db:
#             updated_collection = get_collection_by_id(db, test_collection.id, db_user)
#             assert updated_collection.name == updated_name


import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from fastapi import File, Form
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine, Session

import routes.users as users
import routes.collections as collections
import routes.documents as documents
from utils.security import get_current_user
from models.user import UserCreate
from models.folder import FolderIntake
from models.collection import (
    Collection,
    CollectionInfo,
    CollectionPermissionInfo,
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

# Test create_collection endpoint
@pytest.mark.asyncio
async def test_create_collection(client, get_test_db):
    test_data = {
        "transaction_address":"0x123abc"
    }
    files = {'file': ('test_file.txt', open('test_file.txt', 'rb'))}

    response = client.post("/collections/", data=test_data, files=files)
    assert response.status_code == 200

    collection_info = response.json()
    assert collection_info == response.json()
    assert collection_info["message"] == "Collection created successfully"
    assert "uuid" in collection_info

# Test download_collection endpoint
@pytest.mark.asyncio
async def test_download_collection(client, get_test_db):
    async with get_test_db() as db:
        # Create a test collection
        test_collection = Collection(name="Test Collection")
        db.add(test_collection)
        db.commit()
        db.refresh(test_collection)

        # Send a GET request to download the collection
        response = await client.get(f"/collections/download?col_uuid={test_collection.id}")
        assert response.status_code == 200
        assert response.content is not None

# Test get_all_collections endpoint
@pytest.mark.asyncio
async def test_get_all_collections(client, get_test_db):
    async with get_test_db() as db:
        # Create test collections
        test_collections = [
            Collection(name="Collection 1", owner_id="test_owner_id"),
            Collection(name="Collection 2", owner_id="test_owner_id"),
            Collection(name="Collection 3", owner_id="test_owner_id"),
        ]
        db.add_all(test_collections)
        db.commit()

    # Send a GET request to fetch all collections
    response = await client.get("/collections/")
    assert response.status_code == 200

    collections_list = response.json()
    assert len(collections_list) == len(test_collections)

    for collection_data in collections_list:
        assert any(
            collection_data["name"] == collection.name for collection in test_collections
        )

# Test get_user_collections endpoint
@pytest.mark.asyncio
async def test_get_user_collections(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create some test collections associated with the user
        test_collections = [
            Collection(name="Collection 1", owner_id=db_user.id),
            Collection(name="Collection 2", owner_id=db_user.id),
            Collection(name="Collection 3", owner_id=db_user.id),
        ]
        db.add_all(test_collections)
        db.commit()

    # Authenticate the test user
    login_data = {"username": "test@example.com", "password": "password"}
    login_response = await client.post("/login", data=login_data)

    # Extract the authentication token from the login response
    auth_token = login_response.json()["access_token"]

    # Set the authentication token in the client headers
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Send a GET request to fetch the user's collections
    response = await client.get("/collections/user", headers=headers)
    assert response.status_code == 200

    user_collections = response.json()
    assert len(user_collections) == len(test_collections)

    for collection_data in user_collections:
        assert collection_data["owner_id"] == db_user.id

# Test get_shared_collection endpoint
@pytest.mark.asyncio
async def test_get_shared_collection(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create a test collection associated with the user
        test_collection = Collection(name="Test Collection", owner_id=db_user.id)
        db.add(test_collection)
        db.commit()

        # Create a shared UUID for the collection
        shared_uuid = uuid.uuid4()

        # Create a shared link for the collection with an email
        shared_link = f"/collections/shared?col_uuid={test_collection.id}&email=test@example.com"

    # Send a GET request to fetch the shared collection information
    response = await client.get(shared_link)
    assert response.status_code == 200

    collection_info = response.json()
    assert collection_info["name"] == "Test Collection"
    assert collection_info["owner_id"] == db_user.id

# Test get_collection_hierarchy endpoint
@pytest.mark.asyncio
async def test_get_collection_hierarchy(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create a test collection associated with the user
        test_collection = Collection(name="Test Collection", owner_id=db_user.id)
        db.add(test_collection)
        db.commit()

        # Create a hierarchy of folders for the collection
        root_folder = Folder(name="Root", collection_id=test_collection.id)
        db.add(root_folder)
        db.commit()

        subfolder1 = Folder(name="Subfolder1", collection_id=test_collection.id, parent_id=root_folder.id)
        db.add(subfolder1)
        db.commit()

        subfolder2 = Folder(name="Subfolder2", collection_id=test_collection.id, parent_id=root_folder.id)
        db.add(subfolder2)
        db.commit()

        # Send a GET request to fetch the collection hierarchy
        response = await client.get(f"/collections/hierarchy?col_uuid={test_collection.id}")

    assert response.status_code == 200

    folder_hierarchy = response.json()
    assert folder_hierarchy["name"] == "Root"
    assert len(folder_hierarchy["children"]) == 2

# Test delete_collection endpoint
@pytest.mark.asyncio
async def test_delete_collection(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create a test collection associated with the user
        test_collection = Collection(name="Test Collection", owner_id=db_user.id)
        db.add(test_collection)
        db.commit()

        # Send a DELETE request to delete the collection
        response = await client.delete(f"/collections/?col_uuid={test_collection.id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Collection deleted successfully"

        deleted_collection = db.get(Collection, test_collection.id)
        assert deleted_collection is None

# Test add_permission endpoint
@pytest.mark.asyncio
async def test_add_permission(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create a test collection associated with the user
        test_collection = Collection(name="Test Collection", owner_id=db_user.id)
        db.add(test_collection)
        db.commit()

        # Define test permission
        test_permission = Permission(read=True, write=True)

        # Add permission for the test user
        test_data = {
            "col_uuid": test_collection.id,
            "permission": test_permission.dict(),
            "email": "test@example.com" 
        }
        response = await client.post("/collections/permissions", json=test_data)
        assert response.status_code == 200
        assert response.json()["message"] == "Permission added successfully"

# Test get_permissions endpoint
@pytest.mark.asyncio
async def test_get_permissions(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create a test collection associated with the user
        test_collection = Collection(name="Test Collection", owner_id=db_user.id)
        db.add(test_collection)
        db.commit()

        # Add permission for the test user to the test collection
        test_permission = Permission(read=True, write=True)
        collections.add_permission(db, test_collection, db_user, test_permission, db_user)
        db.commit()

        # Send a GET request to retrieve permissions
        response = await client.get(f"/collections/permissions?col_uuid={test_collection.id}")
        assert response.status_code == 200

        permissions = response.json()
        assert isinstance(permissions, list)
        assert len(permissions) == 1  # Assuming only one permission is added ?
        assert permissions[0]["email"] == "test@example.com"
        assert permissions[0]["read"] == True
        assert permissions[0]["write"] == True

# Test remove_permission endpoint
@pytest.mark.asyncio
async def test_remove_permission(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create a test collection associated with the user
        test_collection = Collection(name="Test Collection", owner_id=db_user.id)
        db.add(test_collection)
        db.commit()

        # Add permission for the test user to the test collection
        test_permission = Permission(read=True, write=True)
        collections.add_permission(db, test_collection, db_user, test_permission, db_user)
        db.commit()

        # Send a DELETE request to remove permission
        response = await client.delete(
            f"/collections/permissions?col_uuid={test_collection.id}&email=test@example.com",
            json=test_permission.dict(),
        )
        assert response.status_code == 200
        assert response.json() == {"message": "Permission removed successfully"}

# Test filter_documents endpoint
@pytest.mark.asyncio
async def test_filter_documents(client, get_test_db):
    # Create a test user
    async with get_test_db() as db:
        test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
        db_user = users.create_user(db, user=test_user)
        db.commit()

        # Create a test collection associated with the user
        test_collection = Collection(name="Test Collection", owner_id=db_user.id)
        db.add(test_collection)
        db.commit()

        # Create some test documents for the collection
        test_documents = [
            Document(name=f"Document{i}.txt", size=1024 * i, owner_id=db_user.id, collection_id=test_collection.id)
            for i in range(1, 4)
        ]
        db.add_all(test_documents)
        db.commit()

        # Send a GET request to filter documents by name
        response_name_filter = await client.get(
            f"/collections/{test_collection.id}/filter?name=Document1.txt"
        )
        assert response_name_filter.status_code == 200
        assert len(response_name_filter.json()) == 1
        assert response_name_filter.json()[0]["name"] == "Document1.txt"

        # Send a GET request to filter documents by max_size
        response_max_size_filter = await client.get(
            f"/collections/{test_collection.id}/filter?max_size=2048"
        )
        assert response_max_size_filter.status_code == 200
        assert len(response_max_size_filter.json()) == 2
        assert all(doc["size"] <= 2048 for doc in response_max_size_filter.json())

        # Send a GET request to filter documents by last_access
        response_last_access_filter = await client.get(
            f"/collections/{test_collection.id}/filter?last_access=2024-05-30T12:00:00"
        )
        assert response_last_access_filter.status_code == 200
        assert len(response_last_access_filter.json()) == 3

    # Test update_collection_name endpoint
    @pytest.mark.asyncio
    async def test_update_collection_name(client, get_test_db):
        # Create a test user
        async with get_test_db() as db:
            test_user = UserCreate(name="Test User", email="test@example.com", password="password", nic="1234567890")
            db_user = users.create_user(db, user=test_user)
            db.commit()

            # Create a test collection associated with the user
            test_collection = Collection(name="Test Collection", owner_id=db_user.id)
            db.add(test_collection)
            db.commit()

            # Send a PUT request to update the collection name
            updated_name = "Updated Collection Name"
            response = await client.put(f"/collections/name?col_uuid={test_collection.id}&name={updated_name}")
            assert response.status_code == 200
            assert response.json()["message"] == "Collection name updated successfully"

            async with get_test_db() as db:
                updated_collection = collections.get_collection_by_id(db, test_collection.id, db_user)
                assert updated_collection.name == updated_name

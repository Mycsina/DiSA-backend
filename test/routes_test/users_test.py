from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine

import routes.collections as collections
import routes.documents as documents
import routes.users as users
from utils.security import get_current_user

# Set up the database URL to point to your test database
SQLALCHEMY_DATABASE_URL = "sqlite:///../test.db"
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


@pytest.fixture
def user_data():
    return {"name": "test_user", "email": "test@example.com", "password": "password123"}


# Test register_user endpoint - success
def test_register_user_success(client, user_data):
    with patch("routes.users.users.create_user") as mock_create_user, patch(
        "routes.users.users.update_user_token"
    ) as mock_update_user_token:

        mock_create_user.return_value = Mock(name=user_data["name"], id="user_id")
        mock_update_user_token.return_value = Mock(token="access_token")

        response = client.post("/users/", json=user_data)

        assert response.status_code == 200
        assert (
            "{{'message': 'User {} created successfully', 'token': 'access_token'}}".format(user_data["name"])
            in response.text
        )

        mock_create_user.assert_called_once()
        mock_update_user_token.assert_called_once()


# Test register_user endpoint - error - internal server error
def test_register_user_internal_server_error(client, user_data):
    with patch("routes.users.users.create_user") as mock_create_user:
        mock_create_user.side_effect = Exception("Database error")

        response = client.post("/users/", json=user_data)

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert "Database error" in response.text

        mock_create_user.assert_called_once()


# Test register_with_cmd endpoint - success
def test_register_with_cmd_success(client):
    with patch("routes.users.users.create_cmd_user") as mock_create_cmd_user, patch(
        "routes.users.users.retrieve_nic"
    ) as mock_retrieve_nic, patch("routes.users.users.create_access_token") as mock_create_access_token, patch(
        "routes.users.users.update_user_token"
    ) as mock_update_user_token:

        mock_create_cmd_user.return_value = Mock(name="test_user")
        mock_retrieve_nic.return_value = ("123456789", "test_user")
        mock_create_access_token.return_value = "access_token"
        mock_update_user_token.return_value = Mock()

        response = client.post("/users/cmd", json={"cmd_token": "test_token"})

        assert response.status_code == 200
        assert '{"message": "User test_user created successfully.", "token": "access_token"}' in response.text

        mock_create_cmd_user.assert_called_once()
        mock_retrieve_nic.assert_called_once_with("test_token")
        mock_create_access_token.assert_called_once_with(data={"sub": "user_id"})
        mock_update_user_token.assert_called_once()


# Test register_with_cmd endpoint - error - internal server error
def test_register_with_cmd_error_internal_server_error(client):
    with patch("routes.users.users.create_cmd_user") as mock_create_cmd_user, patch(
        "routes.users.users.retrieve_nic"
    ) as mock_retrieve_nic:

        mock_create_cmd_user.side_effect = Exception("Database error")
        mock_retrieve_nic.return_value = ("123456789", "test_user")

        response = client.post("/users/cmd", json={"cmd_token": "test_token"})

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert "Database error" in response.text

        mock_create_cmd_user.assert_called_once()
        mock_retrieve_nic.assert_called_once_with("test_token")


# Test login_with_user_password endpoint - success
def test_login_with_user_password_success(client):
    with patch("routes.users.users.verify_user") as mock_verify_user, patch(
        "routes.users.users.create_access_token"
    ) as mock_create_access_token, patch("routes.users.users.update_user_token") as mock_update_user_token:

        mock_verify_user.return_value = Mock(name="test_user", id="user_id")
        mock_create_access_token.return_value = "access_token"
        mock_update_user_token.return_value = Mock()

        response = client.post("/users/login/", data={"username": "test_user", "password": "password123"})

        assert response.status_code == 200
        assert '{"access_token": "access_token", "token_type": "Bearer"}' in response.text

        mock_verify_user.assert_called_once()
        mock_create_access_token.assert_called_once_with(data={"sub": "user_id"})
        mock_update_user_token.assert_called_once()


# Test login_with_user_password endpoint - error - invalid credentials
def test_login_with_user_password_error_invalid_credentials(client):
    with patch("routes.users.users.verify_user") as mock_verify_user:
        mock_verify_user.return_value = None

        response = client.post("/users/login/", data={"username": "test_user", "password": "invalid_password"})

        assert response.status_code == HTTPStatus.UNAUTHORIZED

        mock_verify_user.assert_called_once()


# Test login_with_cmd endpoint - success
def test_login_with_cmd_success(client, user_data):
    from models.user import User

    with patch("routes.users.users.retrieve_nic") as mock_retrieve_nic:
        with patch("routes.users.users.get_user_by_nic") as mock_get_user_by_nic:
            mock_retrieve_nic.return_value = ("1234567890", user_data["name"])
            mock_get_user_by_nic.return_value = User(id=1, name=user_data["name"])

            response = client.get("/users/login/cmd?id_token=mock_id_token")

            assert response.status_code == 200
            assert '{"access_token": "mock_access_token", "token_type": "Bearer"}' in response.text

            mock_retrieve_nic.assert_called_once_with("mock_id_token")
            mock_get_user_by_nic.assert_called_once()


# Test login_with_cmd endpoint - error - user not found
def test_login_with_cmd_error_user_not_found(client):
    with patch("routes.users.users.retrieve_nic") as mock_retrieve_nic:
        with patch("routes.users.users.get_user_by_nic") as mock_get_user_by_nic:
            mock_retrieve_nic.return_value = ("1234567890", "test_user")
            mock_get_user_by_nic.return_value = None

            response = client.get("/users/login/cmd?id_token=mock_id_token")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

            mock_retrieve_nic.assert_called_once_with("mock_id_token")
            mock_get_user_by_nic.assert_called_once()


# Test login_with_cmd endpoint - error - internal server error
def test_login_with_cmd_internal_server_error(client):
    with patch("routes.users.users.retrieve_nic") as mock_retrieve_nic:
        with patch("routes.users.users.get_user_by_nic") as mock_get_user_by_nic:
            mock_retrieve_nic.side_effect = Exception("Mocked exception")

            response = client.get("/users/login/cmd?id_token=mock_id_token")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

            mock_retrieve_nic.assert_called_once_with("mock_id_token")
            mock_get_user_by_nic.assert_not_called()

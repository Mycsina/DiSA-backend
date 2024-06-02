from http import HTTPStatus
import os
from tempfile import NamedTemporaryFile
from typing import Any
import uuid
from unittest.mock import MagicMock, Mock, patch

from models.user import User, UserCreate, UserRole
from sqlalchemy.orm import Session
import pytest
import sqlalchemy
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine

import routes.collections as collections
import routes.documents as documents
import routes.users as users
from utils.security import get_current_user
from models.collection import Collection


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




# Test register_user endpoint
@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("routes.users.users.create_user") as mock_create_user:
            random_email = f"example{uuid.uuid4()}@email.com"
            random_nic = f"{uuid.uuid4()}"
            mock_create_user.return_value = User(
                name="test_user",
                email=random_email,
                nic=random_nic,
                password="password",
                role=UserRole.USER
            )

            response = await client.post(
                "/users/",
                json={
                    "name": "test_user",
                    "email": "example@email.com",
                    "password": "password",
                    "nic": "123456789"
                }
            )

            assert response.status_code == 200
            assert "User test_user created successfully" in response.text

            return response



# Test register_with_cmd endpoint
@pytest.mark.asyncio
async def test_register_with_cmd():
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("routes.users.users.create_cmd_user") as mock_create_cmd_user:
            with patch("routes.users.users.retrieve_nic") as mock_retrieve_nic:
                random_email = f"example{uuid.uuid4()}@email.com"
                random_nic = f"{uuid.uuid4()}"
                mock_retrieve_nic.return_value = (random_nic, "test_user")
                mock_create_cmd_user.return_value = User(
                    id=uuid.uuid4(),
                    name="test_user",
                    email=random_email,
                    nic=random_nic,
                    password="password",
                    role=UserRole.USER
                )

                response = await client.post(
                    "/users/cmd",
                    json={
                        "cmd_token": "valid_cmd_token",
                        "password": "password",
                        "email": "example@email.com"
                    }
                )

                assert response.status_code == 200
                assert "User test_user created successfully." in response.text

                return response



# Test login_with_user_password endpoint
@pytest.mark.asyncio
async def test_login_with_user_password():
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("routes.users.verify_user") as mock_verify_user:
            with patch("routes.users.create_access_token") as mock_create_access_token:
                with patch("routes.users.users.update_user_token") as mock_update_user_token:
                    random_email = f"example{uuid.uuid4()}@email.com"
                    random_nic = f"{uuid.uuid4()}"
                    user_id = uuid.uuid4()
                    mock_verify_user.return_value = User(
                        id=user_id,
                        name="test_user",
                        email=random_email,
                        nic=random_nic,
                        password="password",
                        role=UserRole.USER
                    )
                    mock_create_access_token.return_value = "mock_access_token"

                    response = await client.post(
                        "/users/login/",
                        data={
                            "username": random_email,
                            "password": "password"
                        }
                    )

                    assert response.status_code == 200
                    assert response.json() == {
                        "access_token": "mock_access_token",
                        "token_type": "Bearer"
                    }

                    mock_verify_user.assert_called_once()
                    mock_create_access_token.assert_called_once_with(data={"sub": str(user_id)})
                    mock_update_user_token.assert_called_once()

                    return response
                


# Test login_with_cmd endpoint
@pytest.mark.asyncio
async def test_login_with_cmd():
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("routes.users.users.retrieve_nic") as mock_retrieve_nic:
            with patch("routes.users.users.get_user_by_nic") as mock_get_user_by_nic:
                with patch("routes.users.create_access_token") as mock_create_access_token:
                    with patch("routes.users.users.update_user_token") as mock_update_user_token:
                        random_nic = f"{uuid.uuid4()}"
                        random_email = f"example{uuid.uuid4()}@mail.com"
                        user_id = uuid.uuid4()
                        mock_retrieve_nic.return_value = (random_nic, "test_user")
                        mock_get_user_by_nic.return_value = User(
                            id=user_id,
                            name="test_user",
                            email=random_email,
                            nic=random_nic,
                            password="password",
                            role=UserRole.USER
                        )
                        mock_create_access_token.return_value = "mock_access_token"

                        response = await client.get(
                            "/users/login/cmd",
                            params={"id_token": "valid_cmd_token"}
                        )

                        assert response.status_code == 200
                        assert response.json() == {
                            "access_token": "mock_access_token",
                            "token_type": "Bearer"
                        }

                        mock_retrieve_nic.assert_called_once_with("valid_cmd_token")
                        mock_get_user_by_nic.assert_called_once()
                        args, _ = mock_get_user_by_nic.call_args
                        assert isinstance(args[0], Session)
                        assert args[1] == random_nic
                        mock_create_access_token.assert_called_once_with(data={"sub": str(user_id)})
                        mock_update_user_token.assert_called_once()


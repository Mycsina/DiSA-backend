from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import ScalarResult

from models.collection import Collection
from models.user import User

from start import app

from utils.security import oauth2_scheme

from jose import jwt

client=TestClient(app)

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    global email,user,mock_collection
    email="someone@email.com"
    user=User(email=email)
    mock_collection=MagicMock()
    mock_collection.is_deleted.return_value=False
    mock_collection.name="README"

    monkeypatch.setattr(ScalarResult[User],"first",lambda self: user)
    monkeypatch.setattr(ScalarResult[Collection],"first",lambda self: mock_collection)

    yield

def test_download_controller(monkeypatch):
    monkeypatch.setattr("storage.collection.download_collection", mock_fun_async)

    response = client.get("/collections/download?col_uuid=02c87cde-2e21-4f17-b470-1156ff94642b&email="+email)
    assert response.status_code==200
    assert 'attachment; filename="README"' in response.headers["Content-Disposition"]

async def mock_fun_async(db,col,user):
    return "./README.md"

def test_delete_collection_controller(monkeypatch):
    monkeypatch.setattr("storage.collection.delete_collection",lambda db,doc: True)
    monkeypatch.setattr(jwt,"decode",lambda token,SECRET_KEY,algorithms:{"sub":"02c87cde-2e21-4f17-b470-1156ff94642c"})

    app.dependency_overrides[oauth2_scheme]=lambda:"token"

    response=client.delete("/collections?col_uuid=02c87cde-2e21-4f17-b470-1156ff94642b")
    assert response.json()=={"message": "Collection deleted successfully"}
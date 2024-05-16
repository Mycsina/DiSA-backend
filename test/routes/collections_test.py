from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import ScalarResult

from models.collection import Collection
from models.user import User

from start import app

client=TestClient(app)

def test_download_controller(monkeypatch):
    email="someone@email.com"
    user=User(email=email)
    mock_collection=MagicMock()
    mock_collection.is_deleted.return_value=False
    mock_collection.name="README"

    monkeypatch.setattr(ScalarResult[User],"first",lambda self: user)
    monkeypatch.setattr(ScalarResult[Collection],"first",lambda self: mock_collection)
    monkeypatch.setattr("storage.collection.download_collection", mock_fun)

    response = client.get("/collections/download?col_uuid=02c87cde-2e21-4f17-b470-1156ff94642b&email="+email)
    assert response.status_code==200
    assert 'attachment; filename="README"' in response.headers["Content-Disposition"]

async def mock_fun(db,col,user):
    return "./README.md"
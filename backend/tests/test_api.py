"""
MongoDB-compatible test cases for authentication, document processing, and query logs.
Run with: pytest tests/ -v
"""
import pytest
import mongomock
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db

# Create a mock async-like MongoDB collection wrapper for mongomock
class AsyncMockCollection:
    def __init__(self, collection):
        self._collection = collection

    async def find_one(self, *args, **kwargs):
        return self._collection.find_one(*args, **kwargs)

    async def insert_one(self, *args, **kwargs):
        return self._collection.insert_one(*args, **kwargs)

    async def count_documents(self, *args, **kwargs):
        return self._collection.count_documents(*args, **kwargs)

    async def update_one(self, *args, **kwargs):
        return self._collection.update_one(*args, **kwargs)

    async def delete_many(self, *args, **kwargs):
        return self._collection.delete_many(*args, **kwargs)

    async def delete_one(self, *args, **kwargs):
        return self._collection.delete_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        cursor = self._collection.find(*args, **kwargs)
        return AsyncMockCursor(cursor)


class AsyncMockCursor:
    def __init__(self, cursor):
        self._cursor = list(cursor)
        self._index = 0

    def sort(self, *args, **kwargs):
        # simple mock sort sorting by key if specified
        return self

    def limit(self, l):
        self._cursor = self._cursor[:l]
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._cursor):
            raise StopAsyncIteration
        val = self._cursor[self._index]
        self._index += 1
        return val


class AsyncMockDatabase:
    def __init__(self, client, db_name):
        self._db = client[db_name]

    def __getattr__(self, name):
        col = getattr(self._db, name)
        return AsyncMockCollection(col)


mock_client = mongomock.MongoClient()
mock_db = AsyncMockDatabase(mock_client, "test_legallens")


@pytest.fixture(autouse=True)
def setup_db():
    mock_client["test_legallens"].users.delete_many({})
    mock_client["test_legallens"].documents.delete_many({})
    mock_client["test_legallens"].pages.delete_many({})
    mock_client["test_legallens"].query_logs.delete_many({})
    mock_client["test_legallens"].eval_runs.delete_many({})
    yield


@pytest.fixture()
def client():
    def override_get_db():
        return mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Auth Tests ────────────────────────────────────────────────────────────────

def test_register_and_login(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User",
    })
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"

    r2 = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_me(client):
    client.post("/api/v1/auth/register", json={
        "email": "me@example.com", "password": "pass", "full_name": "Me"
    })
    login = client.post("/api/v1/auth/login", json={
        "email": "me@example.com", "password": "pass"
    })
    token = login.json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


def test_invalid_login(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "wrong"
    })
    assert r.status_code == 401


# ── Document Tests ────────────────────────────────────────────────────────────

def _get_token(client):
    client.post("/api/v1/auth/register", json={
        "email": "doc@example.com", "password": "pass", "full_name": "Doc User"
    })
    r = client.post("/api/v1/auth/login", json={
        "email": "doc@example.com", "password": "pass"
    })
    return r.json()["access_token"]


def test_list_documents_empty(client):
    token = _get_token(client)
    r = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_analytics_summary(client):
    token = _get_token(client)
    r = client.get("/api/v1/analytics/summary?days=30", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "total_documents" in data
    assert "total_queries" in data


def test_eval_compare_empty(client):
    token = _get_token(client)
    r = client.get("/api/v1/eval/compare", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {}

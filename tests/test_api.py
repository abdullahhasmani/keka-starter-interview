import pytest
from fastapi.testclient import TestClient

from app.api.routes import _repo
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_storage():
    _repo.clear()


def test_create_and_get_account():
    r = client.post("/api/accounts", json={"owner_name": "Abd", "initial_balance": 100})
    assert r.status_code == 201
    body = r.json()
    assert body["owner_name"] == "Abd"

    r2 = client.get(f"/api/accounts/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"]


def test_duplicate_owner_is_conflict():
    client.post("/api/accounts", json={"owner_name": "Abd"})
    r = client.post("/api/accounts", json={"owner_name": "  abd "})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"


@pytest.mark.parametrize("payload", [
    {},                                              # missing field
    {"owner_name": "   "},                           # blank
    {"owner_name": "A", "initial_balance": -5},      # negative
    {"owner_name": "A", "initial_balance": "abc"},   # wrong type
])
def test_bad_input_returns_400(payload):
    r = client.post("/api/accounts", json=payload)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_account_is_404():
    r = client.get("/api/accounts/does-not-exist")
    assert r.status_code == 404

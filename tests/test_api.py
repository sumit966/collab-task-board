"""Tests for Collaborative Task Board API."""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def _register(username=None):
    username = username or f"u_{os.urandom(4).hex()}"
    r = client.post("/register", json={"username": username, "password": "testpass123", "role": "member"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"], username


def test_root():
    r = client.get("/")
    assert r.status_code == 200


def test_health():
    r = client.get("/health")
    assert r.status_code == 200


def test_register_and_me():
    token, username = _register()
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == username


def test_unauthorized():
    r = client.get("/me")
    assert r.status_code == 401


def test_board_and_task_flow():
    token, _ = _register()
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/boards", json={"name": "Test Board"}, headers=headers)
    assert r.status_code == 200
    board_id = r.json()["id"]

    r = client.post("/tasks", json={"board_id": board_id, "title": "Write tests"}, headers=headers)
    assert r.status_code == 200
    task_id = r.json()["id"]

    r = client.patch(f"/tasks/{task_id}", json={"status": "in_progress"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"

    r = client.get(f"/boards/{board_id}/tasks", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

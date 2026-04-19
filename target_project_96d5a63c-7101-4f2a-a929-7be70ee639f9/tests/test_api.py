import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_todos_initial():
    response = client.get("/api/todos")
    data = response.json()
    assert data["code"] == 200
    assert len(data["data"]) == 3
    assert all(isinstance(todo["id"], int) for todo in data["data"])

def test_create_todo_valid():
    payload = {"title": "Test Task", "completed": False}
    response = client.post("/api/todos", json=payload)
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["title"] == "Test Task"
    assert data["data"]["completed"] is False

def test_create_todo_invalid_title():
    payload = {"title": "", "completed": False}
    response = client.post("/api/todos", json=payload)
    assert response.status_code == 422

def test_update_todo_success():
    response = client.put("/api/todos/1", json={"completed": True})
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["completed"] is True

def test_update_todo_not_found():
    response = client.put("/api/todos/999", json={"completed": True})
    assert response.status_code == 404

def test_delete_todo_success():
    response = client.delete("/api/todos/1")
    data = response.json()
    assert data["code"] == 200
    
    # Verify deletion
    get_response = client.get("/api/todos")
    todos = get_response.json()["data"]
    assert not any(todo["id"] == 1 for todo in todos)

def test_delete_todo_not_found():
    response = client.delete("/api/todos/999")
    assert response.status_code == 404
import pytest
from fastapi.testclient import TestClient
from backend.main import app, fake_db, current_id

# 初始化测试客户端
client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db():
    """每个测试前重置数据库状态"""
    global fake_db, current_id
    fake_db.clear()
    current_id = 0
    yield
    fake_db.clear()
    current_id = 0

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_todos_initial():
    # 初始有3条预设数据
    response = client.get("/api/todos")
    data = response.json()["data"]
    assert len(data) == 3
    assert all(isinstance(item["id"], int) for item in data)

def test_create_todo():
    payload = {"title": "New Task", "completed": False}
    response = client.post("/api/todos", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "New Task"
    assert data["completed"] is False
    assert data["id"] == 1

def test_create_todo_empty_title():
    payload = {"title": "", "completed": False}
    response = client.post("/api/todos", json=payload)
    assert response.status_code == 422

def test_update_todo():
    # 先创建任务
    create_resp = client.post("/api/todos", json={"title": "Update Me", "completed": False})
    todo_id = create_resp.json()["data"]["id"]
    
    # 更新标题
    update_payload = {"title": "Updated Title"}
    response = client.put(f"/api/todos/{todo_id}", json=update_payload)
    assert response.status_code == 200
    updated_data = response.json()["data"]
    assert updated_data["title"] == "Updated Title"
    assert updated_data["completed"] is False

def test_update_nonexistent_todo():
    response = client.put("/api/todos/999", json={"title": "Test"})
    assert response.status_code == 404

def test_delete_todo():
    # 创建并删除
    create_resp = client.post("/api/todos", json={"title": "Delete Me", "completed": False})
    todo_id = create_resp.json()["data"]["id"]
    
    delete_response = client.delete(f"/api/todos/{todo_id}")
    assert delete_response.status_code == 200
    
    # 验证已删除
    get_response = client.get("/api/todos")
    remaining_ids = [item["id"] for item in get_response.json()["data"]]
    assert todo_id not in remaining_ids

def test_delete_nonexistent_todo():
    response = client.delete("/api/todos/999")
    assert response.status_code == 404

def test_todo_title_length_limit():
    long_title = "A" * 101
    response = client.post("/api/todos", json={"title": long_title, "completed": False})
    assert response.status_code == 422
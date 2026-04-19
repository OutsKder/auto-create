import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    """测试健康检查接口"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_items_initial_data():
    """测试初始数据库存预警逻辑"""
    response = client.get("/api/items")
    data = response.json()
    assert data["code"] == 200
    items = data["data"]
    assert len(items) > 0
    
    # 验证初始化数据的库存预警
    sample_item = items[0]
    expected_warning = sample_item["current_stock"] < 5
    assert sample_item["low_stock_warning"] == expected_warning

def test_create_item_with_low_stock():
    """测试创建低库存物品并验证预警"""
    new_item = {
        "name": "Test Low Stock",
        "description": "Test description",
        "unit_price": 10.99,
        "current_stock": 3
    }
    
    # 创建物品
    create_response = client.post("/api/items", json=new_item)
    assert create_response.status_code == 200
    result = create_response.json()
    assert result["code"] == 200
    assert result["data"]["name"] == "Test Low Stock"
    assert result["data"]["current_stock"] == 3
    
    # 验证获取列表时的预警标识
    get_response = client.get("/api/items")
    items = get_response.json()["data"]
    target_item = next(item for item in items if item["name"] == "Test Low Stock")
    assert target_item["low_stock_warning"] is True

def test_create_item_normal_stock():
    """测试正常库存物品无预警"""
    new_item = {
        "name": "Normal Stock Item",
        "unit_price": 5.00,
        "current_stock": 10
    }
    
    create_response = client.post("/api/items", json=new_item)
    assert create_response.status_code == 200
    
    get_response = client.get("/api/items")
    items = get_response.json()["data"]
    target_item = next(item for item in items if item["name"] == "Normal Stock Item")
    assert target_item["low_stock_warning"] is False

def test_decimal_precision():
    """测试价格精度保留两位小数"""
    new_item = {
        "name": "Precision Test",
        "unit_price": 123.456,
        "current_stock": 5
    }
    
    create_response = client.post("/api/items", json=new_item)
    result = create_response.json()
    # Pydantic会自动处理Decimal精度，这里验证序列化结果
    assert float(result["data"]["unit_price"]) == 123.46

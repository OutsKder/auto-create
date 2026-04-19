from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from decimal import Decimal

app = FastAPI(title="Template API System")

# 启用 CORS，配合前端使用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 模拟数据库与模型 --- #
# AI Agent: 可根据业务在此修改或拆分到单独的 database.py 和 schemas.py
class Item(BaseModel):
    name: str
    description: str | None = None
    unit_price: Decimal
    current_stock: int

class ItemInDB(Item):
    id: int

fake_db: list[ItemInDB] = [
    ItemInDB(id=1, name="示例商品A", description="这是初始化生成的数据", unit_price=Decimal("0.00"), current_stock=0)
]

# --- 业务路由区 --- #

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Service is running"}

@app.get("/api/items")
def get_items():
    # 为每个资产添加低库存预警标识
    result = []
    for item in fake_db:
        item_dict = item.model_dump()
        item_dict["low_stock_warning"] = item.current_stock < 5
        result.append(item_dict)
    return {"code": 200, "data": result}

@app.post("/api/items")
def create_item(item: Item):
    new_id = len(fake_db) + 1
    db_item = ItemInDB(id=new_id, **item.model_dump())
    fake_db.append(db_item)
    return {"code": 200, "message": "添加成功", "data": db_item}

# AI Agent 可以在下面追加新的路由，如：
# @app.post("/api/login")
# @app.put("/api/users")
# ...

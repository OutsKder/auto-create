from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

app = FastAPI(title="Todo List API", description="A beautiful and complete Todo List backend.", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    completed: bool = Field(default=False)

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    completed: Optional[bool] = None

class TodoInDB(TodoBase):
    id: int

fake_db: List[TodoInDB] = []
current_id = 0

def get_next_id():
    global current_id
    current_id += 1
    return current_id

fake_db.append(TodoInDB(id=get_next_id(), title="完善待办事项 (Todo) 的后端 CRUD 逻辑", completed=True))
fake_db.append(TodoInDB(id=get_next_id(), title="将前台界面设计得漂亮一点", completed=True))
fake_db.append(TodoInDB(id=get_next_id(), title="体验智能飞书 Agent 生成代码应用", completed=False))
fake_db.sort(key=lambda x: x.id, reverse=True)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/todos")
def get_todos():
    return {"code": 200, "message": "success", "data": fake_db}

@app.post("/api/todos")
def create_todo(todo: TodoCreate):
    new_todo = TodoInDB(id=get_next_id(), **todo.model_dump())
    fake_db.insert(0, new_todo)
    return {"code": 200, "message": "添加成功", "data": new_todo}

@app.put("/api/todos/{todo_id}")
def update_todo(todo_id: int, todo_update: TodoUpdate):
    for i, t in enumerate(fake_db):
        if t.id == todo_id:
            update_data = todo_update.model_dump(exclude_unset=True)
            updated_item = t.model_copy(update=update_data)
            fake_db[i] = updated_item
            return {"code": 200, "message": "更新成功", "data": updated_item}
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int):
    for i, t in enumerate(fake_db):
        if t.id == todo_id:
            del fake_db[i]
            return {"code": 200, "message": "删除成功"}
    raise HTTPException(status_code=404, detail="Todo not found")
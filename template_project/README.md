# 核心骨架业务系统模板 (Template Project)

这是一个包含基础前后端分离架构的现成模板项目。
**设计目的**：为了让 AI Agent（尤其是 Coder Agent）能够在执行需求方案时，直接跳过繁琐的脚手架搭建与基础设施配置阶段。Agent 只需要阅读此说明，然后直接去修改/新增对应的业务路由或前端展示组件即可快速完成交付。

## 目录结构
```text
template_project/
├── backend/               # 后端目录 (Python FastAPI)
│   ├── main.py            # 主程序入口 & 路由注册
│   ├── requirements.txt   # 依赖清单
│   └── database.py        # 伪造的本地内存数据库或DB连接层
├── frontend/              # 前端目录 (原生 HTML/JS/CSS + Bootstrap)
│   ├── index.html         # 首页界面
│   ├── app.js             # 页面核心交互逻辑与 API 调用
│   └── style.css          # 自定义样式
└── README.md              # 模板接口说明（本文件）
```

## 后端 API 接口说明 (Base URL: `http://localhost:8000`)

目前的模板项目内置了两组通用的 RESTful 接口作为参考基准，AI 可在此基础上通过阅读业务逻辑直接增删改查。

### 1. 健康检测接口
- **GET** `/api/health`
- **功能**: 检查后端服务是否存活。
- **返回**: `{"status": "ok", "message": "Service is running"}`

### 2. 基础数据增删改查 (以 Item 为例)

#### 获取所有数据
- **GET** `/api/items`
- **功能**: 获取当前系统中的所有 Item 列表。
- **返回**: 
  ```json
  {
      "code": 200,
      "data": [
          {"id": 1, "name": "示例商品A", "description": "这是一个测试数据"}
      ]
  }
  ```

#### 添加新数据
- **POST** `/api/items`
- **功能**: 向系统添加一条新数据。
- **请求体 (JSON)**: 
  ```json
  {
      "name": "商品名称",
      "description": "商品描述"
  }
  ```
- **返回**: `{"code": 200, "message": "添加成功", "data": {"id": 2, "name": "...", "description": "..."}}`

## AI Agent 业务微调指北

当你（Agent）接收到新需求时：
1. **不要重构整个框架！**
2. **后端开发**：直接在 `backend/main.py` 中寻找对应的路由进行修改，或者参考 `/api/items` 的写法新增业务 API 类。数据可暂存在 `database.py` 中使用字典/列表模拟。
3. **前端开发**：直接在 `frontend/index.html` 增加相关的视图容器，并在 `frontend/app.js` 增加 `fetch` API 调用渲染即可。
4. 完成修改后，使用 `uvicorn main:app --reload` 跑起来验证通过即可。
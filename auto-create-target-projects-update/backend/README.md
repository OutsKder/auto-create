# Backend 目录说明

`backend` 当前以两个核心子目录为主：

- `api_first/`：对外 API + Pipeline 调度状态机
- `agent/`：Agent 实现（角色、Prompt、LLM Provider、回调）

## 当前目录职责

- `api_first/`
  - `scheduler_api.py`：FastAPI 路由入口（Pipeline 调度接口）
  - `service.py`：调度服务层（阶段推进、Agent 接入）
  - `pipeline.py` / `stage.py` / `checkpoint.py`：流程状态模型
  - `test_pipeline_lifecycle.py`：流程生命周期测试

- `agent/`
  - `agents/`：业务 Agent（如 `requirement_analyst.py`）
  - `llm/`：LLM 抽象、工厂、Provider 实现
  - `tests/`：Agent 相关测试
  - `prompts/`：Prompt 模板与管理
  - `base.py` / `callbacks.py`：Agent 基类与观测回调

- 根目录辅助文件
  - `doubao_llm.py`：兼容转发入口（真实实现下沉到 `agent/llm/legacy_doubao_client.py`）
  - `test_requirement_analyst.py`：兼容测试入口（转发到 `agent/tests/test_requirement_analyst.py`）
  - `test_llm_providers.py`：兼容测试入口（转发到 `agent/tests/test_llm_providers.py`）
  - `requirements.txt`：依赖清单

## 已完成整理项（保持兼容）

- 已将根目录测试脚本迁移到 `agent/tests/`
- 已在根目录保留同名薄包装文件，旧命令仍可继续使用
- 已将 `doubao_llm.py` 实现下沉到 `agent/llm/legacy_doubao_client.py`

## 运行建议

- 执行 `api_first` 测试时，建议在 `auto-create/backend` 目录下运行，并使用本地 venv 解释器：
  - `./venv/Scripts/python.exe -m unittest api_first.test_pipeline_lifecycle`


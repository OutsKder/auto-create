# 前后端 Pipeline API 对接说明

## 目标

前端已经预留统一 API client：`formal-create/main-site/src/api/pipelineApi.ts`。

当前它已经支持真实后端 adapter + mock 兜底。设置 `VITE_PIPELINE_API_BASE_URL` 后会请求后端；不设置时继续使用前端 mock，方便离线预览。

## 后端共识接口

| 前端方法 | 后端 REST 接口 | 用途 |
| --- | --- | --- |
| `createPipeline(input)` | `POST /pipelines` | 根据自然语言需求创建流水线草稿 |
| `runPipeline(pipelineId)` | `POST /pipelines/{id}/run` | 确认计划后启动流水线 |
| `getPipeline(pipelineId)` | `GET /pipelines/{id}` | 查询流水线状态、日志、检查点、产物 |
| `approveCheckpoint(checkpointId)` | `POST /checkpoints/{id}/approve` | 通过人工审批点 |
| `rejectCheckpoint(checkpointId, input)` | `POST /checkpoints/{id}/reject` | 退回人工审批点，并可附带原因 |

## 状态机

前端按后端共识保留以下状态：

```text
CREATED -> RUNNING -> WAITING_APPROVAL -> FINISHED
```

含义：

| 状态 | 前端展示 |
| --- | --- |
| `CREATED` | 已生成计划，等待用户确认启动 |
| `RUNNING` | AI 正在执行流水线 |
| `WAITING_APPROVAL` | 停在人工审批点，等待 Approve / Reject |
| `FINISHED` | 已生成交付包和 MR |

## 前端预留类型

```ts
type PipelineState = "CREATED" | "RUNNING" | "WAITING_APPROVAL" | "FINISHED";
type StageStatus = "PENDING" | "RUNNING" | "DONE" | "WAITING_APPROVAL";

type PipelineStage = {
  id: string;
  name: string;
  status: StageStatus;
  meta: {
    input?: string;
    output?: string;
    acceptance?: string[];
  };
};

type Pipeline = {
  id: string;
  requirement: string;
  state: PipelineState;
  currentStageIndex: number;
  currentStage?: PipelineStage;
  stages: PipelineStage[];
  checkpoint?: PipelineCheckpoint;
  artifacts: PipelineArtifact[];
  logs: PipelineLog[];
  context?: Record<string, unknown>;
};

type PipelineCheckpoint = {
  id: string;
  title: string;
  summary: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  stageId?: string;
  stageName?: string;
  stageIndex?: number;
};

type PipelineArtifact = {
  id: string;
  title: string;
  type: "REQUIREMENT_DOC" | "ARCHITECTURE" | "TEST_REPORT" | "MERGE_REQUEST";
  summary: string;
};

type PipelineLog = {
  id: string;
  level: "INFO" | "SUCCESS" | "WAITING";
  message: string;
};
```

## 当前真实后端接入

当前已接入后端目录：

```text
auto-create-target-projects-update/backend/api_first
```

本地 demo server：

```bash
cd auto-create-target-projects-update
conda run -n byte python -m backend.api_first.http_demo_server
```

默认地址：

```text
http://127.0.0.1:8008
```

前端环境变量（推荐通过 Vite proxy，避免浏览器 CORS/preflight 问题）：

```text
VITE_PIPELINE_API_BASE_URL=/api-pipeline
```

`formal-create/main-site/vite.config.ts` 会把 `/api-pipeline/*` 转发到 `http://127.0.0.1:8008/*`。

真实后端返回字段映射：

| 后端字段 | 前端字段 | 说明 |
| --- | --- | --- |
| `status` | `state` | 整条 Pipeline 状态 |
| `current_stage_index` | `currentStageIndex` | 当前阶段下标 |
| `current_stage` | `currentStage` | 当前后端阶段 |
| `stages` | `stages` | 六阶段真实状态，驱动 Console 左侧流程 |
| `checkpoint.stage_*` | `checkpoint.stage*` | 具体审批点所属阶段 |
| `context.requirement_raw` | `requirement` | 原始用户需求 |
| `context` | `context` / `artifacts` | 阶段产物来源，前端会映射为交付物摘要 |

## 当前 mock 行为

不设置 `VITE_PIPELINE_API_BASE_URL` 时，`pipelineApi.ts` 使用 mock：

1. `createPipeline`
   - 返回固定示例 `PIP-2046`
   - 状态为 `CREATED`
   - 生成六阶段 `stages`

2. `runPipeline`
   - 状态进入 `RUNNING`
   - 前端随后调用 `getPipeline`
   - mock 会在约 900ms 后进入 `WAITING_APPROVAL`

3. `getPipeline`
   - 返回当前流水线状态
   - 会根据 mock 时间推进返回检查点或交付包

4. `approveCheckpoint`
   - 状态先回到 `RUNNING`
   - mock 会在约 700ms 后进入 `FINISHED`

5. `rejectCheckpoint`
   - 状态回到 `CREATED`
   - 前端保留已生成计划，等待用户补充约束或重新确认

## 后端建议返回字段

后端真实接口当前至少返回：

```json
{
  "id": "pipeline-id",
  "status": "WAITING_APPROVAL",
  "current_stage_index": 1,
  "current_stage": {
    "id": "design",
    "name": "方案设计",
    "status": "DONE",
    "meta": {
      "input": "结构化需求 + 代码库上下文",
      "output": "技术方案（含文件变更清单、API 设计）",
      "acceptance": []
    }
  },
  "stages": [],
  "checkpoint": {
    "id": "checkpoint-id",
    "stage_id": "design",
    "stage_name": "方案设计",
    "stage_index": 1,
    "status": "PENDING",
    "note": ""
  },
  "context": {
    "requirement_raw": "给博客增加评论功能..."
  }
}
```

## 前端接入位置

当前 Console 页面只通过以下文件调用流水线能力：

```text
formal-create/main-site/src/api/pipelineApi.ts
```

当前接入链路：

```text
Console UI -> pipelineApi.ts -> 后端 REST API
```

不要在页面组件中直接写后端 URL，这样能保持 mock 和真实后端可切换。

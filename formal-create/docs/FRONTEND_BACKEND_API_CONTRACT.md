# 前后端 Pipeline API 对接说明

## 目标

前端已经预留统一 API client：`formal-create/main-site/src/api/pipelineApi.ts`。

当前它使用 mock 实现，让 Console 可以先完整体验；后续接真实后端时，只需要替换这个文件中的实现，页面组件不需要重写。

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

type Pipeline = {
  id: string;
  requirement: string;
  state: PipelineState;
  checkpoint?: PipelineCheckpoint;
  artifacts: PipelineArtifact[];
  logs: PipelineLog[];
};

type PipelineCheckpoint = {
  id: string;
  title: string;
  summary: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
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

## 当前 mock 行为

当前 `pipelineApi.ts` 的行为如下：

1. `createPipeline`
   - 返回固定示例 `PIP-2046`
   - 状态为 `CREATED`
   - 用于模拟“交付计划已生成”

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

后端真实接口建议至少返回：

```json
{
  "id": "PIP-2046",
  "requirement": "给博客增加评论功能...",
  "state": "WAITING_APPROVAL",
  "checkpoint": {
    "id": "CHK-ARCH-001",
    "title": "架构方案等待审批",
    "summary": "请确认评论 API、审核状态和敏感词过滤策略是否符合交付目标。",
    "status": "PENDING"
  },
  "artifacts": [],
  "logs": [
    {
      "id": "LOG-001",
      "level": "SUCCESS",
      "message": "requirement.normalized"
    }
  ]
}
```

## 前端接入位置

当前 Console 页面只通过以下文件调用流水线能力：

```text
formal-create/main-site/src/api/pipelineApi.ts
```

后续接真实后端时，优先替换这个文件中的 mock 方法为 `fetch` 请求：

```text
Console UI -> pipelineApi.ts -> 后端 REST API
```

不要在页面组件中直接写后端 URL，这样能保持 mock 和真实后端可切换。

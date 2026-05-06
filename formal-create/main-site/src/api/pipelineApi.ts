export type PipelineState = "CREATED" | "RUNNING" | "WAITING_APPROVAL" | "FINISHED";
export type StageStatus = "PENDING" | "RUNNING" | "DONE" | "WAITING_APPROVAL";

export type PipelineStage = {
  id: string;
  name: string;
  status: StageStatus;
  meta: {
    input?: string;
    output?: string;
    acceptance?: string[];
    [key: string]: unknown;
  };
};

export type PipelineCheckpoint = {
  id: string;
  title: string;
  summary: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  stageId?: string;
  stageName?: string;
  stageIndex?: number;
};

export type PipelineArtifact = {
  id: string;
  title: string;
  type: "REQUIREMENT_DOC" | "ARCHITECTURE" | "TEST_REPORT" | "MERGE_REQUEST";
  summary: string;
};

export type PipelineLog = {
  id: string;
  level: "INFO" | "SUCCESS" | "WAITING";
  message: string;
};

export type Pipeline = {
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

export type CreatePipelineInput = {
  requirement: string;
};

export type RejectCheckpointInput = {
  reason?: string;
};

export type ApproveCheckpointInput = {
  note?: string;
  contextPatch?: Record<string, unknown>;
};

type BackendStage = {
  id: string;
  name: string;
  status: StageStatus;
  meta?: PipelineStage["meta"];
};

type BackendCheckpoint = {
  id: string;
  stage_id: string;
  stage_name: string;
  stage_index: number;
  status: "PENDING" | "APPROVED" | "REJECTED";
  note?: string | null;
  context_snapshot?: Record<string, unknown>;
  meta?: Record<string, unknown>;
};

type BackendPipeline = {
  id: string;
  status: PipelineState;
  current_stage_index?: number;
  current_stage?: BackendStage | null;
  stages?: BackendStage[];
  checkpoint?: BackendCheckpoint | null;
  context?: Record<string, unknown>;
};

type MockPipelineRecord = Pipeline & {
  runStartedAt?: number;
  approvedAt?: number;
};

const API_BASE_URL = (import.meta.env.VITE_PIPELINE_API_BASE_URL || "").replace(/\/$/, "");
const BACKEND_DEMO_MODE = import.meta.env.VITE_PIPELINE_DEMO_MODE === "true";
const MOCK_PIPELINE_ID = "PIP-2046";
const MOCK_CHECKPOINT_ID = "CHK-DESIGN-001";

let mockPipeline: MockPipelineRecord | null = null;

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function deepMerge(target: Record<string, unknown>, patch: Record<string, unknown>) {
  Object.entries(patch).forEach(([key, value]) => {
    const current = target[key];
    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      current &&
      typeof current === "object" &&
      !Array.isArray(current)
    ) {
      target[key] = deepMerge(
        { ...(current as Record<string, unknown>) },
        value as Record<string, unknown>
      );
    } else {
      target[key] = value;
    }
  });
  return target;
}

function hasBackend() {
  return API_BASE_URL.length > 0;
}

async function requestBackend<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Backend request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function defaultStages(): PipelineStage[] {
  return [
    {
      id: "analysis",
      name: "需求分析",
      status: "PENDING",
      meta: {
        input: "自然语言需求描述",
        output: "结构化需求文档（含验收标准）",
        acceptance: ["需求范围和边界明确", "歧义项被标记", "需求可追踪到验收标准"],
      },
    },
    {
      id: "design",
      name: "方案设计",
      status: "PENDING",
      meta: {
        input: "结构化需求 + 代码库上下文",
        output: "技术方案（含文件变更清单、API 设计）",
        acceptance: ["明确影响模块和风险", "接口兼容策略清晰", "变更文件清单可执行"],
      },
    },
    {
      id: "coding",
      name: "编码实现",
      status: "PENDING",
      meta: {
        input: "技术方案 + 代码库",
        output: "代码变更集（Diff）",
        acceptance: ["实现与技术方案一致", "核心路径可运行", "不引入无关重构"],
      },
    },
    {
      id: "testing",
      name: "测试验证",
      status: "PENDING",
      meta: {
        input: "代码变更集 + 需求",
        output: "测试代码 + 执行结果",
        acceptance: ["覆盖关键路径", "包含边界场景", "失败用例可复现"],
      },
    },
    {
      id: "review",
      name: "代码评审",
      status: "PENDING",
      meta: {
        input: "代码变更集 + 方案 + 测试结果",
        output: "评审报告",
        acceptance: ["正确性/安全性有结论", "高优先级问题有建议", "结论可用于发布决策"],
      },
    },
    {
      id: "delivery",
      name: "交付集成",
      status: "PENDING",
      meta: {
        input: "评审通过的变更集",
        output: "可合并代码变更 + 变更摘要",
        acceptance: ["变更可合并", "交付物与需求对应", "发布说明完整"],
      },
    },
  ];
}

function buildArtifacts(context: Record<string, unknown> = {}): PipelineArtifact[] {
  return [
    {
      id: "ART-REQ-001",
      title: "需求文档",
      type: "REQUIREMENT_DOC",
      summary: context.analysis_doc ? "后端已生成结构化需求分析。" : "用户故事、边界条件和验收标准已整理。",
    },
    {
      id: "ART-ARCH-001",
      title: "架构方案",
      type: "ARCHITECTURE",
      summary: context.design_doc ? "后端已生成技术方案。" : "接口、模块边界和风险已标注。",
    },
    {
      id: "ART-TEST-001",
      title: "测试摘要",
      type: "TEST_REPORT",
      summary: context.test_report ? "后端已生成测试结果。" : "关键路径和边界场景已覆盖。",
    },
    {
      id: "ART-MR-001",
      title: "Merge Request",
      type: "MERGE_REQUEST",
      summary: context.delivery ? "后端交付包已准备。" : "MR 已准备，可进入代码审阅。",
    },
  ];
}

function logsFromStages(stages: PipelineStage[], checkpoint?: PipelineCheckpoint): PipelineLog[] {
  const logs = stages.map((stage, index) => ({
    id: `LOG-STAGE-${index + 1}`,
    level:
      stage.status === "DONE"
        ? ("SUCCESS" as const)
        : stage.status === "WAITING_APPROVAL"
        ? ("WAITING" as const)
        : ("INFO" as const),
    message: `${stage.id}.${stage.status.toLowerCase()}`,
  }));

  if (checkpoint?.status === "PENDING") {
    logs.push({
      id: `LOG-CHK-${checkpoint.id}`,
      level: "WAITING",
      message: `checkpoint.required: ${checkpoint.stageId || checkpoint.id}`,
    });
  }

  return logs;
}

function normalizeBackendPipeline(data: BackendPipeline): Pipeline {
  const stages = (data.stages?.length ? data.stages : defaultStages()).map((stage) => ({
    id: stage.id,
    name: stage.name,
    status: stage.status,
    meta: stage.meta || {},
  }));

  const checkpoint = data.checkpoint
    ? {
        id: data.checkpoint.id,
        title: `${data.checkpoint.stage_name}等待审批`,
        summary:
          data.checkpoint.note ||
          `请确认「${data.checkpoint.stage_name}」阶段产物是否符合要求，通过后进入下一阶段。`,
        status: data.checkpoint.status,
        stageId: data.checkpoint.stage_id,
        stageName: data.checkpoint.stage_name,
        stageIndex: data.checkpoint.stage_index,
      }
    : undefined;

  const requirement = String(data.context?.requirement_raw || "");

  return {
    id: data.id,
    requirement,
    state: data.status,
    currentStageIndex: data.current_stage_index ?? 0,
    currentStage: data.current_stage
      ? {
          id: data.current_stage.id,
          name: data.current_stage.name,
          status: data.current_stage.status,
          meta: data.current_stage.meta || {},
        }
      : undefined,
    stages,
    checkpoint,
    artifacts: data.status === "FINISHED" ? buildArtifacts(data.context) : [],
    logs: logsFromStages(stages, checkpoint),
    context: data.context,
  };
}

function normalizeMockPipeline(record: MockPipelineRecord): Pipeline {
  const now = Date.now();

  if (record.state === "RUNNING" && record.approvedAt && now - record.approvedAt > 700) {
    record.state = "FINISHED";
    record.stages = record.stages.map((stage) => ({ ...stage, status: "DONE" }));
    record.currentStageIndex = record.stages.length - 1;
    record.currentStage = record.stages[record.currentStageIndex];
    record.checkpoint = {
      id: MOCK_CHECKPOINT_ID,
      title: "方案设计已审批",
      summary: "人工审批已通过，流水线完成编码、测试、评审和交付。",
      status: "APPROVED",
      stageId: "design",
      stageName: "方案设计",
      stageIndex: 1,
    };
    record.artifacts = buildArtifacts(record.context);
  }

  if (
    record.state === "RUNNING" &&
    record.runStartedAt &&
    !record.approvedAt &&
    now - record.runStartedAt > 900
  ) {
    record.state = "WAITING_APPROVAL";
    record.currentStageIndex = 1;
    record.stages = record.stages.map((stage, index) => ({
      ...stage,
      status: index === 0 ? "DONE" : index === 1 ? "DONE" : "PENDING",
    }));
    record.currentStage = record.stages[1];
    record.checkpoint = {
      id: MOCK_CHECKPOINT_ID,
      title: "方案设计等待审批",
      summary: "请确认评论 API、审核状态和敏感词过滤策略是否符合交付目标。",
      status: "PENDING",
      stageId: "design",
      stageName: "方案设计",
      stageIndex: 1,
    };
  }

  return {
    ...record,
    logs: logsFromStages(record.stages, record.checkpoint),
  };
}

export const pipelineApi = {
  async createPipeline(input: CreatePipelineInput): Promise<Pipeline> {
    if (hasBackend()) {
      const data = await requestBackend<BackendPipeline>("/pipelines", {
        method: "POST",
        body: JSON.stringify({
          requirement_raw: input.requirement,
          demo_mode: BACKEND_DEMO_MODE,
          context: BACKEND_DEMO_MODE ? { demo_mode: true } : {},
        }),
      });
      return normalizeBackendPipeline(data);
    }

    await wait(260);
    const stages = defaultStages();
    mockPipeline = {
      id: MOCK_PIPELINE_ID,
      requirement: input.requirement,
      state: "CREATED",
      currentStageIndex: 0,
      currentStage: stages[0],
      stages,
      artifacts: [],
      logs: [],
      context: { requirement_raw: input.requirement },
    };
    return normalizeMockPipeline(mockPipeline);
  },

  async runPipeline(pipelineId: string): Promise<Pipeline> {
    if (hasBackend()) {
      const data = await requestBackend<BackendPipeline>(`/pipelines/${pipelineId}/run`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      return normalizeBackendPipeline(data);
    }

    await wait(260);
    if (!mockPipeline || mockPipeline.id !== pipelineId) {
      throw new Error("Pipeline not found");
    }

    mockPipeline.state = "RUNNING";
    mockPipeline.runStartedAt = Date.now();
    mockPipeline.approvedAt = undefined;
    mockPipeline.checkpoint = undefined;
    mockPipeline.currentStageIndex = 1;
    mockPipeline.stages = mockPipeline.stages.map((stage, index) => ({
      ...stage,
      status: index === 0 ? "DONE" : index === 1 ? "RUNNING" : "PENDING",
    }));
    mockPipeline.currentStage = mockPipeline.stages[1];
    return normalizeMockPipeline(mockPipeline);
  },

  async getPipeline(pipelineId: string): Promise<Pipeline> {
    if (hasBackend()) {
      const data = await requestBackend<BackendPipeline>(`/pipelines/${pipelineId}`);
      return normalizeBackendPipeline(data);
    }

    await wait(120);
    if (!mockPipeline || mockPipeline.id !== pipelineId) {
      throw new Error("Pipeline not found");
    }

    return normalizeMockPipeline(mockPipeline);
  },

  async approveCheckpoint(
    checkpointId: string,
    input: ApproveCheckpointInput = {}
  ): Promise<Pipeline> {
    if (hasBackend()) {
      const data = await requestBackend<BackendPipeline>(`/checkpoints/${checkpointId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          note: input.note || "前端审批通过",
          context_patch: input.contextPatch || undefined,
        }),
      });
      return normalizeBackendPipeline(data);
    }

    await wait(220);
    if (!mockPipeline || mockPipeline.checkpoint?.id !== checkpointId) {
      throw new Error("Checkpoint not found");
    }

    if (input.contextPatch) {
      mockPipeline.context = deepMerge(
        { ...(mockPipeline.context || {}) },
        input.contextPatch
      );
    }
    mockPipeline.state = "RUNNING";
    mockPipeline.approvedAt = Date.now();
    return normalizeMockPipeline(mockPipeline);
  },

  async rejectCheckpoint(
    checkpointId: string,
    input: RejectCheckpointInput = {}
  ): Promise<Pipeline> {
    if (hasBackend()) {
      const data = await requestBackend<BackendPipeline>(`/checkpoints/${checkpointId}/reject`, {
        method: "POST",
        body: JSON.stringify({ note: input.reason || "需要补充约束后重新执行当前阶段" }),
      });
      return normalizeBackendPipeline(data);
    }

    await wait(220);
    if (!mockPipeline || mockPipeline.checkpoint?.id !== checkpointId) {
      throw new Error("Checkpoint not found");
    }

    mockPipeline.state = "CREATED";
    mockPipeline.runStartedAt = undefined;
    mockPipeline.approvedAt = undefined;
    mockPipeline.checkpoint = {
      id: checkpointId,
      title: "方案设计已退回",
      summary: input.reason || "需要补充约束后重新生成执行计划。",
      status: "REJECTED",
      stageId: "design",
      stageName: "方案设计",
      stageIndex: 1,
    };
    mockPipeline.stages = mockPipeline.stages.map((stage, index) => ({
      ...stage,
      status: index === 0 ? "DONE" : "PENDING",
    }));
    mockPipeline.currentStageIndex = 1;
    mockPipeline.currentStage = mockPipeline.stages[1];
    return normalizeMockPipeline(mockPipeline);
  },
};

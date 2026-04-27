export type PipelineState = "CREATED" | "RUNNING" | "WAITING_APPROVAL" | "FINISHED";

export type PipelineCheckpoint = {
  id: string;
  title: string;
  summary: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
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
  checkpoint?: PipelineCheckpoint;
  artifacts: PipelineArtifact[];
  logs: PipelineLog[];
};

export type CreatePipelineInput = {
  requirement: string;
};

export type RejectCheckpointInput = {
  reason?: string;
};

type MockPipelineRecord = Pipeline & {
  runStartedAt?: number;
  approvedAt?: number;
};

const MOCK_PIPELINE_ID = "PIP-2046";
const MOCK_CHECKPOINT_ID = "CHK-ARCH-001";

let mockPipeline: MockPipelineRecord | null = null;

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function buildArtifacts(): PipelineArtifact[] {
  return [
    {
      id: "ART-REQ-001",
      title: "需求文档",
      type: "REQUIREMENT_DOC",
      summary: "用户故事、边界条件和验收标准已整理。",
    },
    {
      id: "ART-ARCH-001",
      title: "架构方案",
      type: "ARCHITECTURE",
      summary: "评论 API、审核状态和敏感词过滤模块已标注。",
    },
    {
      id: "ART-TEST-001",
      title: "测试摘要",
      type: "TEST_REPORT",
      summary: "评论、审核、敏感词拦截场景已覆盖。",
    },
    {
      id: "ART-MR-001",
      title: "Merge Request",
      type: "MERGE_REQUEST",
      summary: "MR #2046 已准备，可进入代码审阅。",
    },
  ];
}

function baseLogs(): PipelineLog[] {
  return [
    { id: "LOG-001", level: "SUCCESS", message: "requirement.normalized" },
    { id: "LOG-002", level: "SUCCESS", message: "stories.generated: 3" },
    { id: "LOG-003", level: "INFO", message: "architecture.drafting..." },
  ];
}

function normalizePipeline(record: MockPipelineRecord): Pipeline {
  const now = Date.now();

  if (record.state === "RUNNING" && record.approvedAt && now - record.approvedAt > 700) {
    record.state = "FINISHED";
    record.checkpoint = {
      id: MOCK_CHECKPOINT_ID,
      title: "架构方案已审批",
      summary: "人工审批已通过，流水线完成代码、测试和 MR 交付。",
      status: "APPROVED",
    };
    record.artifacts = buildArtifacts();
    record.logs = [
      ...baseLogs(),
      { id: "LOG-004", level: "SUCCESS", message: "checkpoint.approved: architecture_v1" },
      { id: "LOG-005", level: "SUCCESS", message: "delivery.package.ready" },
    ];
  }

  if (
    record.state === "RUNNING" &&
    record.runStartedAt &&
    !record.approvedAt &&
    now - record.runStartedAt > 900
  ) {
    record.state = "WAITING_APPROVAL";
    record.checkpoint = {
      id: MOCK_CHECKPOINT_ID,
      title: "架构方案等待审批",
      summary: "请确认评论 API、审核状态和敏感词过滤策略是否符合交付目标。",
      status: "PENDING",
    };
    record.logs = [
      ...baseLogs(),
      { id: "LOG-004", level: "WAITING", message: "checkpoint.required: architecture_v1" },
    ];
  }

  return {
    id: record.id,
    requirement: record.requirement,
    state: record.state,
    checkpoint: record.checkpoint,
    artifacts: record.artifacts,
    logs: record.logs,
  };
}

export const pipelineApi = {
  async createPipeline(input: CreatePipelineInput): Promise<Pipeline> {
    await wait(260);
    mockPipeline = {
      id: MOCK_PIPELINE_ID,
      requirement: input.requirement,
      state: "CREATED",
      artifacts: [],
      logs: [{ id: "LOG-001", level: "SUCCESS", message: "pipeline.created" }],
    };
    return normalizePipeline(mockPipeline);
  },

  async runPipeline(pipelineId: string): Promise<Pipeline> {
    await wait(260);
    if (!mockPipeline || mockPipeline.id !== pipelineId) {
      throw new Error("Pipeline not found");
    }

    mockPipeline.state = "RUNNING";
    mockPipeline.runStartedAt = Date.now();
    mockPipeline.approvedAt = undefined;
    mockPipeline.checkpoint = undefined;
    mockPipeline.logs = baseLogs();
    return normalizePipeline(mockPipeline);
  },

  async getPipeline(pipelineId: string): Promise<Pipeline> {
    await wait(120);
    if (!mockPipeline || mockPipeline.id !== pipelineId) {
      throw new Error("Pipeline not found");
    }

    return normalizePipeline(mockPipeline);
  },

  async approveCheckpoint(checkpointId: string): Promise<Pipeline> {
    await wait(220);
    if (!mockPipeline || mockPipeline.checkpoint?.id !== checkpointId) {
      throw new Error("Checkpoint not found");
    }

    mockPipeline.state = "RUNNING";
    mockPipeline.approvedAt = Date.now();
    mockPipeline.logs = [
      ...baseLogs(),
      { id: "LOG-004", level: "SUCCESS", message: "checkpoint.approved: architecture_v1" },
    ];
    return normalizePipeline(mockPipeline);
  },

  async rejectCheckpoint(
    checkpointId: string,
    input: RejectCheckpointInput = {}
  ): Promise<Pipeline> {
    await wait(220);
    if (!mockPipeline || mockPipeline.checkpoint?.id !== checkpointId) {
      throw new Error("Checkpoint not found");
    }

    mockPipeline.state = "CREATED";
    mockPipeline.runStartedAt = undefined;
    mockPipeline.approvedAt = undefined;
    mockPipeline.checkpoint = {
      id: checkpointId,
      title: "架构方案已退回",
      summary: input.reason || "需要补充约束后重新生成执行计划。",
      status: "REJECTED",
    };
    mockPipeline.logs = [
      ...baseLogs(),
      { id: "LOG-004", level: "WAITING", message: "checkpoint.rejected: need_more_constraints" },
    ];
    return normalizePipeline(mockPipeline);
  },
};

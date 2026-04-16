const STORAGE_KEY = "delivery-engine-mvp-v1";

const STAGE_DEFS = [
  { id: "intake", name: "需求录入", requiresReview: false },
  { id: "analysis", name: "需求分析", requiresReview: false },
  { id: "solution", name: "方案设计", requiresReview: true },
  { id: "coding", name: "编码实现", requiresReview: false },
  { id: "testing", name: "测试验证", requiresReview: false },
  { id: "review", name: "评审确认", requiresReview: true },
  { id: "delivery", name: "交付归档", requiresReview: false },
];

const STATUS_LABELS = {
  draft: "草稿",
  pending: "待开始",
  running: "执行中",
  waiting_review: "待审核",
  approved: "已通过",
  rejected: "已驳回",
  completed: "已完成",
  in_progress: "进行中",
  blocked: "待处理",
};

const PRIORITY_LABELS = {
  high: "高优先级",
  medium: "中优先级",
  low: "低优先级",
};

const runtime = {
  timers: new Map(),
};

let state = loadState();

const requirementForm = document.getElementById("requirementForm");
const requirementListEl = document.getElementById("requirementList");
const listCountEl = document.getElementById("listCount");
const overviewPanel = document.getElementById("overviewPanel");
const pipelinePanel = document.getElementById("pipelinePanel");
const summaryPanel = document.getElementById("summaryPanel");
const riskPanel = document.getElementById("riskPanel");
const logPanel = document.getElementById("logPanel");
const searchInput = document.getElementById("searchInput");
const statusFilter = document.getElementById("statusFilter");
const seedDataBtn = document.getElementById("seedDataBtn");
const clearDataBtn = document.getElementById("clearDataBtn");

bindEvents();
render();

function bindEvents() {
  requirementForm.addEventListener("submit", handleRequirementSubmit);
  searchInput.addEventListener("input", renderRequirementList);
  statusFilter.addEventListener("change", renderRequirementList);
  requirementListEl.addEventListener("click", handleRequirementSelection);
  pipelinePanel.addEventListener("click", handlePipelineAction);
  overviewPanel.addEventListener("click", handleOverviewAction);
  seedDataBtn.addEventListener("click", restoreSeedData);
  clearDataBtn.addEventListener("click", clearLocalData);
}

function handleRequirementSubmit(event) {
  event.preventDefault();
  const formData = new FormData(requirementForm);
  const payload = {
    title: String(formData.get("title") || "").trim(),
    background: String(formData.get("background") || "").trim(),
    goal: String(formData.get("goal") || "").trim(),
    constraints: String(formData.get("constraints") || "").trim(),
    priority: String(formData.get("priority") || "medium"),
    owner: String(formData.get("owner") || "待分配").trim() || "待分配",
  };

  const requirement = createRequirement(payload);
  state.requirements.unshift(requirement);
  state.selectedRequirementId = requirement.id;
  addLog(requirement, "intake", "已创建需求并初始化 Pipeline。");
  saveState();
  requirementForm.reset();
  render();
  startOrResumePipeline(requirement.id);
}

function handleRequirementSelection(event) {
  const card = event.target.closest("[data-requirement-id]");
  if (!card) {
    return;
  }

  state.selectedRequirementId = card.dataset.requirementId;
  saveState();
  render();
}

function handleOverviewAction(event) {
  const action = event.target.dataset.action;
  if (!action) {
    return;
  }

  const requirement = getSelectedRequirement();
  if (!requirement) {
    return;
  }

  if (action === "continue") {
    startOrResumePipeline(requirement.id);
  }
}

function handlePipelineAction(event) {
  const button = event.target.closest("[data-action]");
  if (!button) {
    return;
  }

  const action = button.dataset.action;
  const stageId = button.dataset.stageId;
  const requirement = getSelectedRequirement();
  if (!requirement || !stageId) {
    return;
  }

  if (action === "execute") {
    executeStage(requirement.id, stageId, { manual: true });
    return;
  }

  if (action === "approve") {
    approveStage(requirement.id, stageId);
    return;
  }

  if (action === "reject") {
    rejectStage(requirement.id, stageId);
    return;
  }

  if (action === "rerun") {
    rerunFromStage(requirement.id, stageId);
    return;
  }

  if (action === "save-note") {
    const noteField = pipelinePanel.querySelector(`[data-note-stage-id="${stageId}"]`);
    saveStageNote(requirement.id, stageId, noteField ? noteField.value.trim() : "");
  }
}

function restoreSeedData() {
  const confirmed = window.confirm("这会覆盖当前本地保存的数据，确定恢复示例数据吗？");
  if (!confirmed) {
    return;
  }

  stopAllTimers();
  state = buildSeedState();
  saveState();
  render();
}

function clearLocalData() {
  const confirmed = window.confirm("确定清空本地数据吗？此操作不可恢复。");
  if (!confirmed) {
    return;
  }

  stopAllTimers();
  window.localStorage.removeItem(STORAGE_KEY);
  state = buildEmptyState();
  saveState();
  render();
}

function loadState() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return buildSeedState();
    }

    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.requirements)) {
      return buildSeedState();
    }

    return sanitizeState(parsed);
  } catch (error) {
    console.error("Failed to load local data:", error);
    return buildSeedState();
  }
}

function sanitizeState(rawState) {
  return {
    selectedRequirementId:
      rawState.selectedRequirementId ||
      (rawState.requirements[0] ? rawState.requirements[0].id : null),
    requirements: rawState.requirements.map((req) => ({
      ...req,
      logs: Array.isArray(req.logs) ? req.logs : [],
      stages: Array.isArray(req.stages)
        ? req.stages.map((stage) => ({
            ...stage,
            status: stage.status === "running" ? "pending" : stage.status,
          }))
        : [],
    })),
  };
}

function saveState() {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function createRequirement(payload) {
  const now = nowIso();
  const stages = STAGE_DEFS.map((def) => ({
    id: def.id,
    name: def.name,
    requiresReview: def.requiresReview,
    status: def.id === "intake" ? "completed" : "pending",
    output: def.id === "intake" ? buildIntakeOutput(payload) : "",
    note: "",
    risks: [],
    updatedAt: now,
  }));

  return {
    id: createId("req"),
    title: payload.title,
    background: payload.background,
    goal: payload.goal,
    constraints: payload.constraints || "无额外约束",
    priority: payload.priority,
    owner: payload.owner,
    createdAt: now,
    updatedAt: now,
    currentStageId: "analysis",
    overallStatus: "draft",
    logs: [],
    stages,
    deliverySummary: "",
  };
}

function buildSeedState() {
  const first = createRequirement({
    title: "新增审批通知汇总能力",
    background: "审批结果散落在多个会话和通知流里，负责人无法快速知道哪些审批超时、哪些审批需要重点关注。",
    goal: "在工作台中新增审批通知汇总能力，支持每日自动汇总高优审批、提醒待处理事项，并沉淀日报摘要。",
    constraints: "首版 3 天内交付；优先支持桌面端；不接入复杂 BI 能力。",
    priority: "high",
    owner: "产品经理A",
  });

  hydrateRequirementStages(first, "solution");
  addLog(first, "analysis", "示例需求已完成分析，当前等待方案审核。");

  const second = createRequirement({
    title: "项目日报自动生成助手",
    background: "团队每日需要从群聊、待办和文档中手动整理项目日报，重复劳动较多。",
    goal: "自动汇总任务进展、风险和待办事项，生成可直接发送的项目日报。",
    constraints: "首版只处理单项目日报；允许人工二次编辑。",
    priority: "medium",
    owner: "项目负责人B",
  });

  hydrateRequirementStages(second, "delivery");
  second.overallStatus = "completed";
  second.currentStageId = "delivery";
  second.deliverySummary = getStage(second, "delivery").output;
  addLog(second, "delivery", "示例需求已完成交付，可用于查看完整闭环效果。");

  return {
    selectedRequirementId: first.id,
    requirements: [first, second],
  };
}

function buildEmptyState() {
  return {
    selectedRequirementId: null,
    requirements: [],
  };
}

function hydrateRequirementStages(requirement, targetStageId) {
  for (const stageDef of STAGE_DEFS) {
    const stage = getStage(requirement, stageDef.id);
    if (!stage || stage.id === "intake") {
      continue;
    }

    const output = generateStageResult(requirement, stage.id);
    stage.output = output.output;
    stage.risks = output.risks;
    stage.updatedAt = nowIso();

    if (stage.id === targetStageId && stage.requiresReview) {
      stage.status = "waiting_review";
      requirement.currentStageId = stage.id;
      requirement.overallStatus = "in_progress";
      return;
    }

    stage.status = stage.requiresReview ? "approved" : "completed";

    if (stage.id === "delivery") {
      requirement.deliverySummary = stage.output;
      requirement.currentStageId = "delivery";
      requirement.updatedAt = nowIso();
      return;
    }
  }
}

function render() {
  renderRequirementList();
  renderSelectedRequirement();
}

function renderRequirementList() {
  const requirements = getFilteredRequirements();
  listCountEl.textContent = `共 ${requirements.length} 条`;

  if (!requirements.length) {
    requirementListEl.innerHTML = `
      <div class="empty-state">
        当前没有符合筛选条件的需求。你可以新建一个需求，或者恢复示例数据体验完整流程。
      </div>
    `;
    return;
  }

  requirementListEl.innerHTML = requirements
    .map((req) => {
      const currentStage = getCurrentStage(req);
      const activeClass = req.id === state.selectedRequirementId ? "active" : "";
      return `
        <article class="requirement-item ${activeClass}" data-requirement-id="${req.id}">
          <h3 class="requirement-title">${escapeHtml(req.title)}</h3>
          <div class="muted">${escapeHtml(req.owner)} · ${formatDateTime(req.updatedAt)}</div>
          <div class="meta-row">
            ${renderBadge(req.overallStatus, STATUS_LABELS[req.overallStatus] || req.overallStatus)}
            ${renderBadge(req.priority, PRIORITY_LABELS[req.priority] || req.priority, "priority")}
          </div>
          <div class="meta-row">
            ${renderBadge(
              currentStage.status,
              `${currentStage.name} · ${STATUS_LABELS[currentStage.status] || currentStage.status}`
            )}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderSelectedRequirement() {
  const requirement = getSelectedRequirement();
  if (!requirement) {
    renderEmptyPanels();
    return;
  }

  renderOverview(requirement);
  renderPipeline(requirement);
  renderSummary(requirement);
  renderRisks(requirement);
  renderLogs(requirement);
}

function renderEmptyPanels() {
  const emptyMarkup = `
    <div class="panel-heading">
      <h2>当前未选择需求</h2>
    </div>
    <div class="empty-state">
      左侧选中一个需求，或者新建一个需求后即可查看完整的 Pipeline 状态、节点产物和日志记录。
    </div>
  `;

  overviewPanel.innerHTML = emptyMarkup;
  pipelinePanel.innerHTML = emptyMarkup;
  summaryPanel.innerHTML = emptyMarkup;
  riskPanel.innerHTML = emptyMarkup;
  logPanel.innerHTML = emptyMarkup;
}

function renderOverview(requirement) {
  const nextStage = getNextRunnableStage(requirement);
  const currentStage = getCurrentStage(requirement);
  const actionMarkup =
    nextStage && !hasBlockingStage(requirement)
      ? `<button class="primary-btn" data-action="continue">继续自动推进</button>`
      : "";

  overviewPanel.innerHTML = `
    <div class="panel-heading">
      <div>
        <h2>${escapeHtml(requirement.title)}</h2>
        <div class="meta-row">
          ${renderBadge(requirement.overallStatus, STATUS_LABELS[requirement.overallStatus])}
          ${renderBadge(requirement.priority, PRIORITY_LABELS[requirement.priority], "priority")}
        </div>
      </div>
      ${actionMarkup}
    </div>

    <div class="overview-grid">
      <div class="stat-card">
        <div class="stat-label">负责人</div>
        <div class="stat-value">${escapeHtml(requirement.owner)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">当前节点</div>
        <div class="stat-value">${escapeHtml(currentStage.name)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">更新时间</div>
        <div class="stat-value">${formatDateTime(requirement.updatedAt)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">完成进度</div>
        <div class="stat-value">${getCompletionText(requirement)}</div>
      </div>
    </div>

    <div class="description-card">
      <div class="panel-heading">
        <h3>背景</h3>
      </div>
      <p>${escapeHtml(requirement.background)}</p>
    </div>

    <div class="description-card">
      <div class="panel-heading">
        <h3>目标与约束</h3>
      </div>
      <p><strong>目标：</strong>${escapeHtml(requirement.goal)}</p>
      <p><strong>约束：</strong>${escapeHtml(requirement.constraints)}</p>
    </div>
  `;
}

function renderPipeline(requirement) {
  pipelinePanel.innerHTML = `
    <div class="panel-heading">
      <div>
        <h2>Pipeline 看板</h2>
        <span class="hint">自动推进普通节点，方案设计和评审确认需要人工审核</span>
      </div>
    </div>
    <div class="pipeline-grid">
      ${requirement.stages.map((stage) => renderStageCard(requirement, stage)).join("")}
    </div>
  `;
}

function renderStageCard(requirement, stage) {
  const activeClass = requirement.currentStageId === stage.id ? "active" : "";
  const canExecute = canExecuteStage(requirement, stage.id);
  const output = stage.output
    ? `<div class="output-box">${escapeHtml(stage.output)}</div>`
    : `<div class="output-box muted">该节点还没有产出内容。</div>`;

  return `
    <article class="stage-card ${activeClass}">
      <div class="stage-header">
        <div class="stage-title-wrap">
          <h3>${escapeHtml(stage.name)}</h3>
          <div class="stage-meta">最近更新：${formatDateTime(stage.updatedAt)}</div>
        </div>
        ${renderBadge(stage.status, STATUS_LABELS[stage.status] || stage.status)}
      </div>

      <div class="stage-output">
        ${output}
      </div>

      ${renderStageActions(stage, canExecute)}

      <div class="note-editor">
        <label>
          <span class="hint">人工备注 / 补充上下文</span>
          <textarea data-note-stage-id="${stage.id}" placeholder="记录人工修改、驳回原因或补充约束...">${escapeHtml(
            stage.note || ""
          )}</textarea>
        </label>
        <button class="secondary-btn" data-action="save-note" data-stage-id="${stage.id}">保存备注</button>
      </div>
    </article>
  `;
}

function renderStageActions(stage, canExecute) {
  const actions = [];

  if (canExecute) {
    actions.push(
      `<button class="secondary-btn" data-action="execute" data-stage-id="${stage.id}">执行节点</button>`
    );
  }

  if (stage.status === "waiting_review") {
    actions.push(
      `<button class="approve-btn" data-action="approve" data-stage-id="${stage.id}">审核通过</button>`
    );
    actions.push(
      `<button class="reject-btn" data-action="reject" data-stage-id="${stage.id}">驳回重做</button>`
    );
  }

  if (["completed", "approved", "rejected"].includes(stage.status) && stage.id !== "intake") {
    actions.push(
      `<button class="ghost-btn" data-action="rerun" data-stage-id="${stage.id}">从该节点重跑</button>`
    );
  }

  if (stage.status === "running") {
    actions.push(`<button class="ghost-btn" disabled>正在生成中...</button>`);
  }

  return actions.length ? `<div class="stage-actions">${actions.join("")}</div>` : "";
}

function renderSummary(requirement) {
  summaryPanel.innerHTML = `
    <div class="panel-heading">
      <div>
        <h2>交付摘要</h2>
        <span class="hint">当流程完成后，这里会沉淀最终交付结果</span>
      </div>
    </div>
    <div class="delivery-summary">
      <div class="summary-box">
        <p>${escapeHtml(
          requirement.deliverySummary ||
            "当前尚未完成交付。你可以先审核方案设计节点，让流程继续自动推进。"
        )}</p>
      </div>
    </div>
  `;
}

function renderRisks(requirement) {
  const riskItems = requirement.stages.flatMap((stage) =>
    (stage.risks || []).map((risk) => ({
      stageName: stage.name,
      text: risk,
    }))
  );

  if (!riskItems.length) {
    riskPanel.innerHTML = `
      <div class="panel-heading">
        <h2>风险提示</h2>
      </div>
      <div class="empty-state">当前没有高风险提示。随着流程推进，分析、方案和评审阶段会动态产生风险项。</div>
    `;
    return;
  }

  riskPanel.innerHTML = `
    <div class="panel-heading">
      <h2>风险提示</h2>
    </div>
    <div class="risk-list">
      ${riskItems
        .map(
          (risk) => `
          <div class="risk-item">
            <span class="risk-stage">${escapeHtml(risk.stageName)}</span>
            <p>${escapeHtml(risk.text)}</p>
          </div>
        `
        )
        .join("")}
    </div>
  `;
}

function renderLogs(requirement) {
  const logs = [...requirement.logs].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

  if (!logs.length) {
    logPanel.innerHTML = `
      <div class="panel-heading">
        <h2>执行日志</h2>
      </div>
      <div class="empty-state">当前没有日志记录。</div>
    `;
    return;
  }

  logPanel.innerHTML = `
    <div class="panel-heading">
      <h2>执行日志</h2>
    </div>
    <div class="log-list">
      ${logs
        .map(
          (log) => `
          <div class="log-item">
            <time>${formatDateTime(log.createdAt)} · ${escapeHtml(getStageName(log.stageId))}</time>
            <p>${escapeHtml(log.message)}</p>
          </div>
        `
        )
        .join("")}
    </div>
  `;
}

function startOrResumePipeline(requirementId) {
  const requirement = getRequirementById(requirementId);
  if (!requirement) {
    return;
  }

  if (hasBlockingStage(requirement)) {
    render();
    return;
  }

  const nextStage = getNextRunnableStage(requirement);
  if (!nextStage) {
    if (getStage(requirement, "delivery").status === "completed") {
      requirement.overallStatus = "completed";
      requirement.currentStageId = "delivery";
      requirement.deliverySummary = getStage(requirement, "delivery").output;
    }
    requirement.updatedAt = nowIso();
    saveState();
    render();
    return;
  }

  executeStage(requirementId, nextStage.id, { manual: false });
}

function executeStage(requirementId, stageId, options = {}) {
  const requirement = getRequirementById(requirementId);
  const stage = requirement ? getStage(requirement, stageId) : null;
  if (!requirement || !stage) {
    return;
  }

  if (!canExecuteStage(requirement, stageId) && !options.manual) {
    return;
  }

  if (stage.status === "running") {
    return;
  }

  stage.status = "running";
  stage.updatedAt = nowIso();
  requirement.currentStageId = stage.id;
  requirement.overallStatus = "in_progress";
  requirement.updatedAt = nowIso();
  addLog(requirement, stage.id, `已启动 ${stage.name} 节点。`);
  saveState();
  render();

  const timerId = window.setTimeout(() => {
    runtime.timers.delete(buildTimerKey(requirementId, stageId));
    finalizeStage(requirementId, stageId);
  }, 700);

  runtime.timers.set(buildTimerKey(requirementId, stageId), timerId);
}

function finalizeStage(requirementId, stageId) {
  const requirement = getRequirementById(requirementId);
  const stage = requirement ? getStage(requirement, stageId) : null;
  if (!requirement || !stage) {
    return;
  }

  const result = generateStageResult(requirement, stageId);
  stage.output = result.output;
  stage.risks = result.risks;
  stage.updatedAt = nowIso();
  requirement.updatedAt = nowIso();

  if (stage.requiresReview) {
    stage.status = "waiting_review";
    requirement.currentStageId = stage.id;
    requirement.overallStatus = "in_progress";
    addLog(requirement, stage.id, `${stage.name} 已生成结果，等待人工审核。`);
  } else {
    stage.status = "completed";
    requirement.currentStageId = stage.id;
    addLog(requirement, stage.id, `${stage.name} 已完成并产出结构化结果。`);

    if (stage.id === "delivery") {
      requirement.deliverySummary = stage.output;
      requirement.overallStatus = "completed";
      addLog(requirement, stage.id, "需求已完成交付归档。");
    }
  }

  saveState();
  render();

  if (!stage.requiresReview && stage.id !== "delivery") {
    startOrResumePipeline(requirementId);
  }
}

function approveStage(requirementId, stageId) {
  const requirement = getRequirementById(requirementId);
  const stage = requirement ? getStage(requirement, stageId) : null;
  if (!requirement || !stage || stage.status !== "waiting_review") {
    return;
  }

  stage.status = "approved";
  stage.updatedAt = nowIso();
  requirement.updatedAt = nowIso();
  requirement.currentStageId = stage.id;
  requirement.overallStatus = "in_progress";
  addLog(requirement, stage.id, `${stage.name} 已通过人工审核。`);
  saveState();
  render();
  startOrResumePipeline(requirementId);
}

function rejectStage(requirementId, stageId) {
  const requirement = getRequirementById(requirementId);
  const stage = requirement ? getStage(requirement, stageId) : null;
  if (!requirement || !stage || stage.status !== "waiting_review") {
    return;
  }

  stage.status = "rejected";
  stage.updatedAt = nowIso();
  requirement.updatedAt = nowIso();
  requirement.currentStageId = stage.id;
  requirement.overallStatus = "blocked";
  addLog(requirement, stage.id, `${stage.name} 被人工驳回，请补充备注后从当前节点重跑。`);
  saveState();
  render();
}

function rerunFromStage(requirementId, stageId) {
  const requirement = getRequirementById(requirementId);
  const stageIndex = requirement
    ? requirement.stages.findIndex((stage) => stage.id === stageId)
    : -1;

  if (!requirement || stageIndex < 0) {
    return;
  }

  for (let index = stageIndex; index < requirement.stages.length; index += 1) {
    const stage = requirement.stages[index];
    stage.status = stage.id === "intake" ? "completed" : "pending";
    stage.output = stage.id === "intake" ? stage.output : "";
    stage.risks = [];
    stage.note = index === stageIndex ? stage.note : "";
    stage.updatedAt = nowIso();
  }

  requirement.deliverySummary = "";
  requirement.overallStatus = "in_progress";
  requirement.currentStageId = stageId;
  requirement.updatedAt = nowIso();
  addLog(requirement, stageId, `已从 ${getStageName(stageId)} 重新发起流程。`);
  saveState();
  render();
  executeStage(requirementId, stageId, { manual: true });
}

function saveStageNote(requirementId, stageId, note) {
  const requirement = getRequirementById(requirementId);
  const stage = requirement ? getStage(requirement, stageId) : null;
  if (!requirement || !stage) {
    return;
  }

  stage.note = note;
  stage.updatedAt = nowIso();
  requirement.updatedAt = nowIso();
  addLog(requirement, stageId, note ? "已更新人工备注。" : "已清空人工备注。");
  saveState();
  render();
}

function generateStageResult(requirement, stageId) {
  const analysis = getStage(requirement, "analysis");
  const solution = getStage(requirement, "solution");
  const coding = getStage(requirement, "coding");
  const testing = getStage(requirement, "testing");
  const review = getStage(requirement, "review");

  if (stageId === "analysis") {
    return {
      output: [
        "【需求摘要】",
        `1. 核心目标：${requirement.goal}`,
        `2. 用户痛点：${requirement.background}`,
        `3. 范围约束：${requirement.constraints}`,
        "",
        "【AI 识别的澄清问题】",
        "- 是否需要提供历史数据回看能力？",
        "- 需要支持哪些消息入口或通知方式？",
        "- 是否需要给不同角色展示不同视图？",
        "",
        "【建议验收目标】",
        "- 支持按优先级聚合需求信息",
        "- 支持生成结构化交付材料",
        "- 支持关键节点人工确认并保留日志",
      ].join("\n"),
      risks: [
        "原始需求仍存在范围模糊问题，建议在方案阶段确认边界。",
        "需要尽早明确通知入口和展示形式，避免后续返工。",
      ],
    };
  }

  if (stageId === "solution") {
    const noteLine = solution && solution.note ? `- 人工补充：${solution.note}` : "";
    return {
      output: [
        "【技术方案草案】",
        "1. 输入层：接收需求标题、背景、目标、约束、优先级和负责人。",
        "2. 流程层：以固定 Pipeline 驱动需求分析、方案设计、编码、测试、评审和交付。",
        "3. Agent 层：每个节点输出结构化结果，并将结果传递给下游节点。",
        "4. 交互层：方案设计与评审确认由人工审核把关，其余节点自动推进。",
        "",
        "【模块拆解】",
        "- Requirement Intake：需求录入与列表管理",
        "- Workflow Engine：节点状态机与自动推进逻辑",
        "- Agent Runner：不同阶段的产出生成与上下文继承",
        "- Review Console：人工审核、驳回、重跑和备注管理",
        "- Delivery Summary：交付归档与结果沉淀",
        noteLine,
        "",
        "【里程碑建议】",
        "- M1：跑通需求创建和分析、方案阶段",
        "- M2：补齐编码、测试、评审和交付",
        "- M3：完善可视化和日志追踪能力",
      ]
        .filter(Boolean)
        .join("\n"),
      risks: [
        "如果后续接入真实大模型，需要约束输出格式和失败重试策略。",
        "若未来对接真实代码仓库，需补充权限和回滚机制。",
      ],
    };
  }

  if (stageId === "coding") {
    return {
      output: [
        "【实现策略】",
        "- 使用单页应用承载需求列表、流程看板、日志和交付摘要。",
        "- 引入本地状态管理和 localStorage 持久化，确保刷新后仍可继续演示。",
        "- 将流程推进逻辑与页面渲染解耦，便于未来接入真实 Agent。",
        "",
        "【代码任务拆解】",
        "- 定义 Stage/Requirement 数据结构",
        "- 编写流程推进与人工审核逻辑",
        "- 渲染需求列表和节点卡片",
        "- 聚合风险与日志信息",
        "",
        "【示例代码骨架】",
        "function startOrResumePipeline(requirementId) {",
        "  // 找到下一个可执行节点并启动",
        "}",
      ].join("\n"),
      risks: [
        "前端单文件实现便于快速验证，但后续需要拆分模块以提升可维护性。",
      ],
    };
  }

  if (stageId === "testing") {
    return {
      output: [
        "【测试建议】",
        "- 用例 1：创建需求后自动生成分析结果",
        "- 用例 2：方案节点审核通过后应继续推进编码、测试、评审",
        "- 用例 3：方案节点驳回后流程应进入待处理状态",
        "- 用例 4：从任意完成节点重跑后，下游节点应被清空并重新生成",
        "- 用例 5：刷新页面后需求数据应从本地恢复",
        "",
        "【验收清单】",
        "- 需求列表可正常切换",
        "- 节点状态颜色和操作按钮清晰可见",
        "- 日志与风险信息持续同步更新",
      ].join("\n"),
      risks: [
        "当前测试为轻量验证，后续需要补充更细粒度的异常流测试。",
      ],
    };
  }

  if (stageId === "review") {
    return {
      output: [
        "【评审结论】",
        "- 流程闭环完整，已满足 MVP 核心目标。",
        "- 方案审核和评审确认节点的人机协同设计符合题目要求。",
        "- 页面交互清晰，适合在比赛中快速演示完整链路。",
        "",
        "【评审建议】",
        "- 下一步可接入真实 LLM，替换模板化 Agent 输出。",
        "- 可补充流程模板配置能力，支持不同类型需求。",
        "- 可进一步拆分前后端，提高工程扩展性。",
        "",
        "【通过条件】",
        "- 若演示中无关键异常，建议准许进入交付归档。",
      ].join("\n"),
      risks: [
        "在真实业务环境中，需要补充更严格的权限、审计和异常处理机制。",
      ],
    };
  }

  if (stageId === "delivery") {
    const approvalNote = review && review.note ? `人工评审补充：${review.note}` : "人工评审已确认当前版本可交付。";
    return {
      output: [
        `该需求已完成从“需求 -> 方案 -> 编码 -> 测试 -> 评审 -> 交付”的完整闭环。`,
        "",
        "本次交付产物包括：",
        "- 结构化需求分析与验收目标",
        "- 可执行技术方案草案",
        "- 编码实现策略与任务拆解",
        "- 测试建议和验收清单",
        "- 评审结论与后续优化方向",
        "",
        "交付建议：",
        "- 当前版本可用于比赛演示和产品验证",
        "- 后续优先接入真实模型和外部系统集成",
        `- ${approvalNote}`,
      ].join("\n"),
      risks: [],
    };
  }

  return {
    output: analysis ? analysis.output : "暂无内容",
    risks: [],
  };
}

function canExecuteStage(requirement, stageId) {
  const stage = getStage(requirement, stageId);
  if (!stage || ["running", "completed", "approved", "waiting_review"].includes(stage.status)) {
    return false;
  }

  const currentIndex = requirement.stages.findIndex((item) => item.id === stageId);
  const previousStages = requirement.stages.slice(0, currentIndex);
  return previousStages.every((item) =>
    ["completed", "approved"].includes(item.status)
  );
}

function getNextRunnableStage(requirement) {
  return requirement.stages.find(
    (stage) =>
      stage.id !== "intake" &&
      stage.status === "pending" &&
      canExecuteStage(requirement, stage.id)
  );
}

function hasBlockingStage(requirement) {
  return requirement.stages.some((stage) =>
    ["running", "waiting_review", "rejected"].includes(stage.status)
  );
}

function getFilteredRequirements() {
  const keyword = searchInput.value.trim().toLowerCase();
  const status = statusFilter.value;

  return state.requirements.filter((req) => {
    const matchesKeyword =
      !keyword ||
      req.title.toLowerCase().includes(keyword) ||
      req.owner.toLowerCase().includes(keyword);

    const matchesStatus = status === "all" || req.overallStatus === status;
    return matchesKeyword && matchesStatus;
  });
}

function getSelectedRequirement() {
  const selected =
    state.requirements.find((req) => req.id === state.selectedRequirementId) ||
    state.requirements[0] ||
    null;

  if (selected && selected.id !== state.selectedRequirementId) {
    state.selectedRequirementId = selected.id;
    saveState();
  }

  return selected;
}

function getRequirementById(id) {
  return state.requirements.find((req) => req.id === id) || null;
}

function getStage(requirement, stageId) {
  return requirement.stages.find((stage) => stage.id === stageId) || null;
}

function getCurrentStage(requirement) {
  return getStage(requirement, requirement.currentStageId) || requirement.stages[0];
}

function addLog(requirement, stageId, message) {
  requirement.logs.push({
    id: createId("log"),
    stageId,
    message,
    createdAt: nowIso(),
  });
  requirement.updatedAt = nowIso();
}

function buildIntakeOutput(payload) {
  return [
    "【需求录入】",
    `标题：${payload.title}`,
    `背景：${payload.background}`,
    `目标：${payload.goal}`,
    `约束：${payload.constraints || "无额外约束"}`,
    `负责人：${payload.owner}`,
  ].join("\n");
}

function getCompletionText(requirement) {
  const finishedCount = requirement.stages.filter((stage) =>
    ["completed", "approved"].includes(stage.status)
  ).length;
  return `${finishedCount} / ${requirement.stages.length} 节点`;
}

function getStageName(stageId) {
  const stageDef = STAGE_DEFS.find((stage) => stage.id === stageId);
  return stageDef ? stageDef.name : stageId;
}

function renderBadge(status, label, prefix = "status") {
  return `<span class="badge ${prefix}-${status}">${escapeHtml(label)}</span>`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function nowIso() {
  return new Date().toISOString();
}

function createId(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function buildTimerKey(requirementId, stageId) {
  return `${requirementId}:${stageId}`;
}

function stopAllTimers() {
  for (const timerId of runtime.timers.values()) {
    window.clearTimeout(timerId);
  }
  runtime.timers.clear();
}

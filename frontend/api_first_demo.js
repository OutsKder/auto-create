const API_DEFAULT = "http://127.0.0.1:8010";
const STAGE_FIELDS = [
  ["analysis", "需求分析"],
  ["design", "方案设计"],
  ["coding", "代码生成"],
  ["testing", "测试生成"],
  ["review", "代码评审"],
  ["delivery", "交付集成"],
];

const state = {
  baseUrl: API_DEFAULT,
  pipeline: null,
  timeline: [],
  pollTimer: null,
};

const el = {
  baseUrl: document.getElementById("baseUrl"),
  connectBtn: document.getElementById("connectBtn"),
  createBtn: document.getElementById("createBtn"),
  refreshBtn: document.getElementById("refreshBtn"),
  approveBtn: document.getElementById("approveBtn"),
  rejectBtn: document.getElementById("rejectBtn"),
  requirementInput: document.getElementById("requirementInput"),
  connectionStatus: document.getElementById("connectionStatus"),
  pipelineId: document.getElementById("pipelineId"),
  statusSummary: document.getElementById("statusSummary"),
  currentStage: document.getElementById("currentStage"),
  currentCheckpoint: document.getElementById("currentCheckpoint"),
  nextAction: document.getElementById("nextAction"),
  stageOutputs: document.getElementById("stageOutputs"),
  timeline: document.getElementById("timeline"),
};

el.connectBtn.addEventListener("click", async () => {
  state.baseUrl = normalizeBaseUrl(el.baseUrl.value);
  await refreshPipeline();
});
el.createBtn.addEventListener("click", createAndStartPipeline);
el.refreshBtn.addEventListener("click", refreshPipeline);
el.approveBtn.addEventListener("click", () => approveCurrentCheckpoint("approve"));
el.rejectBtn.addEventListener("click", () => approveCurrentCheckpoint("reject"));

el.baseUrl.value = state.baseUrl;
renderEmpty();

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/$/, "") || API_DEFAULT;
}

async function api(path, options = {}) {
  const response = await fetch(`${state.baseUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(`无法解析响应: ${text.slice(0, 200)}`);
  }
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

async function createAndStartPipeline() {
  const requirement = String(el.requirementInput.value || "").trim();
  if (!requirement) {
    alert("请先输入需求");
    return;
  }

  state.baseUrl = normalizeBaseUrl(el.baseUrl.value);
  setConnectionStatus("创建中...");
  stopPolling();
  state.timeline = [];
  renderTimeline();

  try {
    const created = await api("/pipelines", {
      method: "POST",
      body: JSON.stringify({
        requirement_raw: requirement,
        context: { demo_mode: false, source: "api_first_demo_frontend" },
      }),
    });
    pushTimeline("create_pipeline", { requirement_raw: requirement }, created);
    state.pipeline = created;
    renderAll();

    const running = await api(`/pipelines/${created.id}/run`, { method: "POST" });
    pushTimeline("run_pipeline", { pipeline_id: created.id }, running);
    state.pipeline = running;
    renderAll();
    startPolling();
    setConnectionStatus("已连接");
  } catch (error) {
    console.error(error);
    setConnectionStatus(`错误: ${error.message}`);
    alert(error.message);
  }
}

async function refreshPipeline() {
  state.baseUrl = normalizeBaseUrl(el.baseUrl.value);
  if (!state.pipeline?.id) {
    setConnectionStatus("已连接");
    return;
  }

  try {
    const current = await api(`/pipelines/${state.pipeline.id}`);
    state.pipeline = current;
    pushTimeline("get_pipeline", { pipeline_id: current.id }, current);
    renderAll();
    if (current.status === "WAITING_APPROVAL") {
      startPolling();
    } else if (current.status === "FINISHED") {
      stopPolling();
    }
    setConnectionStatus("已连接");
  } catch (error) {
    console.error(error);
    setConnectionStatus(`错误: ${error.message}`);
  }
}

async function approveCurrentCheckpoint(action) {
  if (!state.pipeline?.checkpoint?.id) {
    alert("当前没有可审批的 checkpoint");
    return;
  }

  const checkpoint = state.pipeline.checkpoint;
  const note = window.prompt(`请输入 ${action === "approve" ? "批准" : "驳回"}备注`, "");
  const path = action === "approve"
    ? `/checkpoints/${checkpoint.id}/approve`
    : `/checkpoints/${checkpoint.id}/reject`;

  try {
    const result = await api(path, {
      method: "POST",
      body: JSON.stringify({ note: note || "" }),
    });
    pushTimeline(action, { checkpoint_id: checkpoint.id, note: note || "" }, result);
    state.pipeline = result;
    renderAll();
    if (result.status === "WAITING_APPROVAL") {
      startPolling();
    } else if (result.status === "FINISHED") {
      stopPolling();
    }
  } catch (error) {
    console.error(error);
    alert(error.message);
  }
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(refreshSilently, 1500);
}

function stopPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function refreshSilently() {
  if (!state.pipeline?.id) return;
  try {
    const current = await api(`/pipelines/${state.pipeline.id}`);
    state.pipeline = current;
    renderAll();
    if (current.status === "FINISHED") {
      stopPolling();
    }
  } catch (error) {
    console.error(error);
    stopPolling();
    setConnectionStatus(`轮询失败: ${error.message}`);
  }
}

function pushTimeline(step, request, response) {
  state.timeline.unshift({
    step,
    request,
    response,
    time: new Date().toLocaleTimeString(),
  });
  renderTimeline();
}

function renderEmpty() {
  renderStageOutputs(null);
  renderTimeline();
  renderStatus(null);
  el.pipelineId.textContent = "Pipeline: -";
  el.currentStage.textContent = "-";
  el.currentCheckpoint.textContent = "-";
  el.nextAction.textContent = "-";
  el.approveBtn.disabled = true;
  el.rejectBtn.disabled = true;
}

function renderAll() {
  renderStatus(state.pipeline);
  renderStageOutputs(state.pipeline);
  renderTimeline();
  renderActions(state.pipeline);
}

function renderStatus(pipeline) {
  if (!pipeline) {
    el.statusSummary.textContent = "等待创建流程";
    return;
  }

  el.pipelineId.textContent = `Pipeline: ${pipeline.id}`;
  el.currentStage.textContent = pipeline.current_stage ? `${pipeline.current_stage.name} (${pipeline.current_stage.status})` : "-";
  el.currentCheckpoint.textContent = pipeline.checkpoint ? `${pipeline.checkpoint.stage_name} / ${pipeline.checkpoint.status}` : "-";
  el.nextAction.textContent = formatNextAction(pipeline.next_http);

  const checkpointText = pipeline.checkpoint
    ? `Checkpoint ${pipeline.checkpoint.id}\n阶段: ${pipeline.checkpoint.stage_name}\n状态: ${pipeline.checkpoint.status}\n备注: ${pipeline.checkpoint.note || "-"}`
    : "暂无 checkpoint";

  el.statusSummary.textContent = [
    `状态: ${pipeline.status}`,
    `当前阶段: ${pipeline.current_stage ? pipeline.current_stage.name : "-"}`,
    `下一步: ${formatNextAction(pipeline.next_http)}`,
    checkpointText,
  ].join("\n\n");
}

function renderActions(pipeline) {
  const hasCheckpoint = Boolean(pipeline && pipeline.checkpoint && pipeline.status === "WAITING_APPROVAL");
  el.approveBtn.disabled = !hasCheckpoint;
  el.rejectBtn.disabled = !hasCheckpoint;
}

function renderStageOutputs(pipeline) {
  if (!pipeline) {
    el.stageOutputs.innerHTML = "<div class='stage-item'><div class='stage-title'>暂无流程</div><div class='stage-output'>请先输入需求并创建流程。</div></div>";
    return;
  }

  const context = pipeline.context || {};
  const values = {
    analysis: stringify(context.requirement_structured || context.analysis_doc),
    design: stringify(context.design_doc),
    coding: stringify(context.code_diff),
    testing: stringify(context.test_report),
    review: stringify(context.review_result),
    delivery: stringify(context.delivery),
  };

  el.stageOutputs.innerHTML = STAGE_FIELDS.map(([id, label]) => {
    const status = pipeline.stages.find((item) => item.id === id)?.status || "-";
    return `
      <div class="stage-item">
        <div class="stage-top">
          <div>
            <div class="stage-title">${label}</div>
            <div class="muted">状态: ${status}</div>
          </div>
          <div class="badge">${id}</div>
        </div>
        <div class="stage-output">${escapeHtml(values[id] || "等待产出")}</div>
      </div>
    `;
  }).join("");
}

function renderTimeline() {
  if (!state.timeline.length) {
    el.timeline.innerHTML = "<div class='timeline-item'><div class='timeline-step'>暂无事件</div><div class='timeline-resp'>创建流程后，事件会在这里展示。</div></div>";
    return;
  }

  el.timeline.innerHTML = state.timeline.map((item) => `
    <div class="timeline-item">
      <div class="timeline-step">${item.time} · ${item.step}</div>
      <div class="timeline-req"><strong>请求</strong>\n${escapeHtml(JSON.stringify(item.request, null, 2))}</div>
      <div class="timeline-resp"><strong>响应</strong>\n${escapeHtml(JSON.stringify(item.response, null, 2))}</div>
    </div>
  `).join("");
}

function formatNextAction(nextHttp) {
  if (!nextHttp) return "-";
  if (nextHttp.approve && nextHttp.reject) {
    return `批准 ${nextHttp.approve.path} / 驳回 ${nextHttp.reject.path}`;
  }
  return `${nextHttp.method} ${nextHttp.path}`;
}

function stringify(value) {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br />")
    .replace(/\t/g, "&nbsp;&nbsp;&nbsp;&nbsp;")
    .replace(/ /g, "&nbsp;");
}

function setConnectionStatus(text) {
  el.connectionStatus.textContent = text;
}

# 织界引擎 (ZHIJIE ENGINE) - 整体架构与开发策略

## 1. 赛道定位与目标
本项目旨在实现“基于 AI 驱动的需求交付流程引擎”赛道的前端部分（功能一与功能二）。
核心目标：在 3 天内，以极简、功利、高交付质量的方式，完成与后端 Pipeline 引擎的对接。

## 2. 物理架构解耦
为了保证开发效率和代码纯粹性，前端被物理隔离为两个完全独立的子项目：

### 2.1 `main-site` (主站：官网与控制台)
- **定位**：标准的 React SPA (单页应用)。
- **职责**：展示产品价值（Landing Page），提供 Pipeline 的全局管控视角（Console），处理 Human-in-the-Loop 的审批流。
- **技术栈**：React 18 + Vite + Tailwind CSS + React Router + Zustand。
- **详细设计**：请参考 `MAIN_SITE_PRD.md`。

### 2.2 `ai-widget` (注入式智能悬浮控件)
- **定位**：可注入到任意目标网页的独立脚本（类似 Content Script）。
- **职责**：在目标网页上实现 DOM 圈选、对话交互、以及最核心的**无刷新热更新预览 (HMR)**。
- **技术栈**：React 18 + Vite (打包为单文件) + Tailwind CSS (需注意样式隔离) + Zustand。
- **详细设计**：请参考 `WIDGET_PRD.md`。

## 3. 后端接口契约 (API Contract)
两个前端子项目都必须严格遵循以下极简状态机与 API：

### 3.1 状态机流转
`CREATED` -> `RUNNING` -> `WAITING_APPROVAL` -> `FINISHED`

### 3.2 核心 API
1. **创建 Pipeline**: `POST /pipelines`
2. **启动 Pipeline**: `POST /pipelines/{id}/run`
3. **查询状态**: `GET /pipelines/{id}` (前端需轮询此接口)
4. **审批通过**: `POST /checkpoints/{id}/approve`
5. **审批驳回**: `POST /checkpoints/{id}/reject`

## 4. 3 天冲刺开发节奏 (The 3-Day Sprint)

- **Day 1: 拿下主站基本盘 (`main-site`)**
  - 搭建官网首页 (SaaS 风格)。
  - 搭建控制台，跑通创建 Pipeline 和状态轮询。
- **Day 2: 死磕 Widget 核心交互 (`ai-widget`)**
  - 实现 Widget 注入与 UI 骨架。
  - 攻克“魔法透镜”：DOM 元素圈选与标识提取。
- **Day 3: 攻克难点与精修**
  - 解决 Widget 的实时热更新预览 (HMR) 难题。
  - 召唤 `@dieter-rams-critic` 进行全局视觉打磨。
  - 准备最终演示脚本。

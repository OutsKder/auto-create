# 📄 PRD: Main Site (DevFlow Engine)

## 1. 🎯 Executive Summary
- **Problem Statement**: Traditional software development is a labor-intensive pipeline where information is lost across roles. Current AI tools focus solely on code generation, missing the broader bottlenecks of requirement understanding, architecture design, and code review.
- **Target Audience**: Product Managers, Tech Leads, and Software Engineers.
- **Objective**: Build an AI-driven platform that orchestrates specialized Agents across the entire Software Development Life Cycle (SDLC), utilizing Human-in-the-Loop oversight to safely deliver code from natural language requirements.

## 2. 💡 Proposed Solution
- **Feishu-Style Landing & Dashboard**: A modern, clean SaaS interface for managing projects and viewing active AI development pipelines.
- **Pipeline Orchestration UI**: A visual representation of the DevFlow Engine. Users input a natural language requirement, which triggers the backend state machine.
- **Human-in-the-Loop Checkpoints**: At critical junctures (e.g., Architecture Design, Code Review), the pipeline pauses. Users review the Agent's output and either Approve or Reject the work.
- **Backend State Machine Integration**:
  - The UI uses `POST /pipelines` to create the workflow (State: `CREATED`).
  - The UI uses `POST /pipelines/{id}/run` to start execution (State: `RUNNING`).
  - The UI polls `GET /pipelines/{id}` to update the visual pipeline progress.
  - When the state reaches `WAITING_APPROVAL`, the UI presents a checkpoint interface.
  - Users call `POST /checkpoints/{id}/approve` to proceed or `POST /checkpoints/{id}/reject` to send the Agent back to the previous step (returning state to `RUNNING`).
  - Completion lands the pipeline in the `FINISHED` state.

## 3. 📖 User Stories & Acceptance Criteria
| User Story | Acceptance Criteria | Priority |
|------------|---------------------|----------|
| As a PM, I want to input a natural language requirement, so that the system can automatically create a development pipeline. | - Given the dashboard <br> - When I submit a requirement description <br> - Then a new pipeline is created via `POST /pipelines` and execution begins via `POST /pipelines/{id}/run` | High |
| As a User, I want to visually track the pipeline's progress, so that I know which Agent is currently working. | - Given an active pipeline <br> - When I view the pipeline details page <br> - Then I see real-time status updates polling from `GET /pipelines/{id}` | High |
| As a Tech Lead, I want to review and approve/reject the architecture design, so that I ensure the AI's technical approach is sound. | - Given the pipeline is in `WAITING_APPROVAL` state <br> - When I review the design document <br> - Then I can click Approve (`POST /checkpoints/{id}/approve`) or Reject (`POST /checkpoints/{id}/reject`) | High |

## 4. 🎨 Design & UX Requirements
- **Key Interactions**:
  - The landing page should emulate Feishu's professional SaaS aesthetic (clean typography, ample whitespace, clear CTAs).
  - Real-time visual feedback for pipeline progression (e.g., loading spinners for active nodes, checkmarks for completed nodes).
  - Checkpoint modals must clearly display the Agent's output (e.g., Markdown rendering for design docs, diff viewers for code reviews).
- **Edge Cases**:
  - If a user rejects a checkpoint, the UI must prompt for a "Reject Reason" to pass back to the Agent.
  - If the backend polling fails, gracefully show a reconnecting state.

## 5. 📈 Success Metrics (KPIs)
- **Primary Metric**: Task completion rate (percentage of pipelines that successfully reach the `FINISHED` state).
- **Secondary Metrics**: 
  - Time elapsed from requirement submission to final delivery.
  - Number of rejection loops per checkpoint.
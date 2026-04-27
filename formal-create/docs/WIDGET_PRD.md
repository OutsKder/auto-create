# 📄 PRD: AI Widget (In-Page Modification Flow)

## 1. 🎯 Executive Summary
- **Problem Statement**: Modifying existing UI requires context switching between the browser, IDE, and version control. PMs and Designers lack the ability to directly safely tweak the UI without developer intervention.
- **Target Audience**: Designers, Product Managers, and Frontend Developers.
- **Objective**: Provide an injected floating widget that allows users to select live DOM elements, request changes via natural language, preview results via HMR, and automatically generate Merge Requests.

## 2. 💡 Proposed Solution
- **Injected Floating Control**: A non-intrusive chat widget injected into the target web application.
- **DOM Selection (Point & Click)**: Users can activate a selection mode to hover and circle at least 3 distinct elements (e.g., buttons, text, cards) to establish context.
- **Natural Language Editing & Real-time Preview**: Users type instructions in the widget. The backend Agent modifies the codebase, triggering Vite/Webpack Hot Module Replacement (HMR) for an instant visual preview without a page reload.
- **MR Generation**: Once the user is satisfied with the preview, they confirm the changes, and the Agent automatically generates an MR with a semantic summary and line-level diff.
- **Backend State Machine Integration**:
  - Invoking a UI change creates a background pipeline (`POST /pipelines`) in the `CREATED` state.
  - The agent starts processing the natural language and code modification (`POST /pipelines/{id}/run`, State: `RUNNING`).
  - The widget polls `GET /pipelines/{id}`. Once code is generated and HMR is triggered, the pipeline enters `WAITING_APPROVAL`.
  - The user previews the changes. If they accept, the widget calls `POST /checkpoints/{id}/approve`, generating the MR and moving to `FINISHED`. If they reject, `POST /checkpoints/{id}/reject` is called to refine the changes.

## 3. 📖 User Stories & Acceptance Criteria
| User Story | Acceptance Criteria | Priority |
|------------|---------------------|----------|
| As a Designer, I want to select an element on the live page, so that I can give the AI specific context for my modification. | - Given the floating widget <br> - When I click "Select Element" and hover over the page <br> - Then the hovered DOM elements highlight and can be selected | High |
| As a User, I want to describe my UI change in plain text, so that the AI can modify the code for me. | - Given selected elements <br> - When I submit a prompt (e.g., "Change to primary blue") <br> - Then a pipeline is created and executed in the background | High |
| As a User, I want to see the changes instantly, so that I can verify the modification is correct before committing. | - Given the pipeline is executing <br> - When the code is modified <br> - Then the page updates automatically via HMR without refreshing | High |
| As a PM, I want to approve the change to auto-create an MR, so that the modification is safely integrated into the codebase. | - Given the pipeline is in `WAITING_APPROVAL` <br> - When I click "Looks Good" <br> - Then `approve` API is called, and an MR with a semantic summary is created | High |

## 4. 🎨 Design & UX Requirements
- **Key Interactions**:
  - The widget must be draggable or collapsible so it does not block the underlying UI.
  - DOM selection must use clear visual bounding boxes (e.g., blue dashed borders with an overlay) to indicate the active element.
  - Chat interface should have a typing indicator to show the backend Agent is in the `RUNNING` state modifying code.
- **Edge Cases**:
  - What if the requested change breaks the frontend build? The widget must display the build error and allow the user to provide a follow-up prompt to fix it (effectively calling `reject` with error context).
  - Selecting elements that are deeply nested should have a smart heuristic to grab the most meaningful React/Vue component.

## 5. 📈 Success Metrics (KPIs)
- **Primary Metric**: Number of successful Merge Requests generated directly from the widget.
- **Secondary Metrics**: 
  - Time elapsed from prompt submission to MR creation.
  - User satisfaction score or approval rate of generated UI changes.
# DevFlow Agent Runtime

This package contains the runtime Agent pipeline. It keeps a strict boundary:
Agents produce structured artifacts, while workflows perform side effects such
as patch application and test execution.

## Runtime Chain

```text
RequirementAnalyst
  -> requirement_structured

TechArchitect
  -> design + codebase_context

CodeGeneratorAgent
  -> code_diff

SDETAgent
  -> tests

TestingWorkflow
  -> tests.sandbox_result

SeniorReviewerAgent
  -> review
```

Self-healing uses the same chain and adds `TriageAgent` + `RetryManager` to feed
failure feedback into the next `CodeGeneratorAgent` attempt.

## Main Modules

- `contracts.py`: canonical Pydantic contracts shared by all Agents.
- `base.py`: `BaseAgent` and `AgentConfig`.
- `agents/`: pipeline-facing Agent adapters.
- `codegen/`: code generation core, patching, runner, and `TestingWorkflow`.
- `self_healing/`: orchestration, triage, retry, and self-healing models.
- `llm/`: provider abstraction and default LLM construction.
- `prompts/`: prompt templates used by generation Agents.
- `tools/`: codebase context and retrieval helpers.
- `workspace/`: isolated workspace creation and cleanup.

## Contracts

All cross-Agent data should validate against `contracts.py`. Runtime code should
import data models from `backend.agent.contracts` or from package exports such as
`backend.agent.codegen.Patch`; historical compatibility modules have been
removed.

## Configuration

- `AgentConfig`: shared Agent runtime settings such as temperature, token limit,
  timeout, and retry count.
- `TestingWorkflowConfig`: test execution settings, including Docker usage,
  Docker image, timeout, and sandbox configuration.
- `SelfHealingConfig`: self-healing orchestration settings, including retry
  budget and default testing configuration.

## Side Effects

`SDETAgent` does not run tests and does not write files. It only returns a
structured `TestBundle` with `sandbox_result=None`.

`TestingWorkflow` is the only codegen-layer component that should:

- create an isolated workspace,
- apply `code_diff.patches`,
- materialize generated tests,
- run `runner_commands`,
- fill `tests.sandbox_result`.

This keeps generation deterministic and makes the execution step auditable.

主链路是：
requirement_analyst.py
→ tech_architect.py
→ code_generator.py
→ sdet.py
→ testing_workflow.py
→ patcher.py
→ runner.py

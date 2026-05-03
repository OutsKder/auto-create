# auto-create

## Agent Runtime

The Agent implementation lives in `backend/agent`.

Current runtime boundaries:

```text
Agents produce structured artifacts.
Workflows perform side effects.
Coordinators orchestrate retries and decisions.
```

Primary package imports:

```python
from backend.agent import RequirementAnalyst, TechArchitect
from backend.agent.agents import CodeGeneratorAgent, SDETAgent, SeniorReviewerAgent
from backend.agent.codegen import TestingWorkflow
from backend.agent.self_healing import SelfHealingCoordinator
```

See `backend/agent/README.md` for the trimmed Agent module structure.

"""Run dockerized TestingWorkflow (replay)
This script loads the same input and runs the TestingWorkflow.
"""
import json
from backend.agent.codegen.testing_workflow import TestingWorkflow

with open('test/testing_workflow_input(docker).json','r',encoding='utf-8') as f:
    ctx = json.load(f)
ctx.setdefault('testing_options', {})
ctx['testing_options']['use_docker'] = True
# ensure pytest install in container
if 'tests' in ctx and isinstance(ctx['tests'], dict):
    rc = ctx['tests'].get('runner_commands', []) or []
    ctx['tests']['runner_commands'] = [
        ('pip install -q pytest && ' + c) if c.strip().startswith('pytest') else c for c in rc
    ]

wf = TestingWorkflow(debug_mode=True)
res = wf.execute(ctx)
print(res)

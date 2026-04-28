# auto-create

## Step2 Retrieval Gate

- Quick gate (minimal deterministic checks):

```bash
python backend/agent/run_step2_gate.py
```

- Run baseline evaluation only (Recall/Coverage/Latency):

```bash
python backend/agent/run_step2_eval.py
```

- Gate with baseline evaluation:

```bash
python backend/agent/run_step2_gate.py --with-eval
```

- Full gate (minimal checks + end-to-end chain):

```bash
python backend/agent/run_step2_gate.py --with-e2e
```

- Full gate with evaluation (minimal + eval + e2e):

```bash
python backend/agent/run_step2_gate.py --with-eval --with-e2e
```

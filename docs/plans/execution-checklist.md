<!-- doc-id: execution-checklist -->
# Execution checklist

## Wave 1 — Hosted CI that runs the full suite

| ID | Task | Deliverables | Verification | Done |
| --- | --- | --- | --- | --- |
| T1.1 | Track tasks in an execution checklist that the guards read: the guard of `make check`, the pre-push hook and the push gate read only the `partial` features of `docs/features.md`, so work that is not a product feature had no state that stopped a full run or a push. This checklist holds each task with one of the states `[ ]`, `[~]`, `[o]` and `[!] cause: <cause>; retry: <condition>`; `scripts/docs_check.py` rejects another state, a row without a task ID, a repeated ID, a checklist without rows and a translation whose IDs or states differ, and `scripts/full_run.py` and `scripts/push_gate.py` refuse while a task is `[~]` or the checklist cannot be read | `docs/plans/execution-checklist.md`(.ko), `scripts/docs_check.py`, `scripts/full_run.py`, `scripts/push_gate.py`, `AGENTS.md`(.ko) | `python3 scripts/test.py --unit test_docs_check test_full_run test_push_gate` | [o] |

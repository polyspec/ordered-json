<!-- doc-id: execution-checklist -->
<!-- source-sha256: ed4eb95e7cbadf68cd4d42a0c899bb064a1ef9382141740bd6672f18ea333cdc -->
# 실행 체크리스트

## Wave 1 — 전체 suite를 실행하는 hosted CI

| ID | 작업 | 산출물 | 검증 | 완료 |
| --- | --- | --- | --- | --- |
| T1.1 | guard가 읽는 실행 체크리스트로 작업을 추적: `make check`의 guard, pre-push hook, push gate는 `docs/features.md`의 `partial` 기능만 읽었으므로, 제품 기능이 아닌 작업에는 전체 실행이나 push를 멈추는 상태가 없었다. 이 체크리스트는 각 작업을 `[ ]`, `[~]`, `[o]`, `[!] cause: <cause>; retry: <condition>` 중 하나의 상태로 담는다. `scripts/docs_check.py`는 다른 상태, 작업 ID가 없는 행, 반복된 ID, 행이 없는 체크리스트, ID나 상태가 다른 번역을 거부하고, `scripts/full_run.py`와 `scripts/push_gate.py`는 작업이 `[~]`이거나 체크리스트를 읽을 수 없으면 거부한다 | `docs/plans/execution-checklist.md`(.ko), `scripts/docs_check.py`, `scripts/full_run.py`, `scripts/push_gate.py`, `AGENTS.md`(.ko) | `python3 scripts/test.py --unit test_docs_check test_full_run test_push_gate` | [o] |

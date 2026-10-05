<!-- doc-id: execution-checklist -->
<!-- source-sha256: 3a10df1357154214cc9b05da6fc242496ebeee51a2a9d76f1ea714cd8fc85d33 -->
# 실행 체크리스트

## Wave 1 — 전체 suite를 실행하는 hosted CI

| ID | 작업 | 산출물 | 검증 | 완료 |
| --- | --- | --- | --- | --- |
| T1.1 | guard가 읽는 실행 체크리스트로 작업을 추적: `make check`의 guard, pre-push hook, push gate는 `docs/features.md`의 `partial` 기능만 읽었으므로, 제품 기능이 아닌 작업에는 전체 실행이나 push를 멈추는 상태가 없었다. 이 체크리스트는 각 작업을 `[ ]`, `[~]`, `[o]`, `[!] cause: <cause>; retry: <condition>` 중 하나의 상태로 담는다. `scripts/docs_check.py`는 다른 상태, 작업 ID가 없는 행, 반복된 ID, 행이 없는 체크리스트, ID나 상태가 다른 번역을 거부하고, `scripts/full_run.py`와 `scripts/push_gate.py`는 작업이 `[~]`이거나 체크리스트를 읽을 수 없으면 거부한다 | `docs/plans/execution-checklist.md`(.ko), `scripts/docs_check.py`, `scripts/full_run.py`, `scripts/push_gate.py`, `AGENTS.md`(.ko) | `python3 scripts/test.py --unit test_docs_check test_full_run test_push_gate` | [o] |
| T1.2 | 검사를 offline으로 실행하고 `make tools`에서만 내려받기: cargo, go, npm, Composer는 모든 검사에서 online으로 실행됐으므로 `cargo build --locked`가 `rust/Cargo.lock`의 crate를 필요할 때 내려받았고, PIE PHAR와 추가 사례는 손으로 내려받았다. Makefile은 `CARGO_NET_OFFLINE=true`, `GOPROXY=off`, `npm_config_offline=true`, `COMPOSER_DISABLE_NETWORK=1`을 export하고, `scripts/toolchains.py`는 모든 진입점에 이를 설정하며, `make tools`는 이를 제거한 채(`$(ONLINE)`) 실행한다. `make tools`는 Rust toolchain, npm, crate(`cargo fetch --locked`), `.cache/pie/pie.phar`의 PIE PHAR, `.cache/JSONTestSuite`의 추가 사례를 설치하고 각각을 `external-inputs.json`과 대조한다 | `Makefile`, `scripts/toolchains.py`, `scripts/tests/test_toolchains.py`, `docs/operations/validation.md`(.ko), `AGENTS.md`(.ko) | `python3 scripts/test.py --unit test_toolchains` | [o] |

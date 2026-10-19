<!-- doc-id: checklist-kit-standard -->
<!-- source-sha256: 57df960ebe23883bfe77c677ce1578c3c09889a188adee82324e2d6b82397916 -->
# kit 표준 체크리스트

| ID | Task | Deliverables | Verification | State |
|---|---|---|---|---|
| T2.1 | 저장소는 kit 표준 0.0.54를 따릅니다 | `docs/plans/execution/`, `docs/operations/documentation-plan.md`, `docs/operations/proposals.md`, `packages/js/tests`, `config/layout.yml`, `Makefile`, `.github/workflows/gates.yml`, `config/owner-checks.json` | `make kit-check` | [o] |
| T2.2 | 패키지는 AGENTS, CHANGELOG와 Makefile을 두지 않습니다. 절은 루트 AGENTS와 CHANGELOG로 합치고, 검사는 루트 Makefile의 target이 되며, layout 예외를 제거하고, Composer manifest의 PHP platform은 8.4.1이며 lock을 다시 잠그고, Makefile이 잃은 recipe를 되돌리고, 비교 대상 제품명을 더 이상 적지 않습니다 | `AGENTS.md`(.ko), `CHANGELOG.md`(.ko), `Makefile`, `config/layout.yml`, `composer.json`, `composer.lock`, `packages/php/composer.json`, `packages/php/composer.lock`, `packages/php-ext/composer.json`, `packages/php-ext/composer.lock`, `packages/*/README.md`(.ko), `docs/plans/execution/checklist.md`(.ko) | `make kit-check` and `node node_modules/@polyspec/kit/dist/run-tests.mjs node -- tests/scripts/environment.test.mts` | [o] |

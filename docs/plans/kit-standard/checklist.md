<!-- doc-id: checklist-kit-standard -->
# Kit standard checklist

| ID | Task | Deliverables | Verification | State |
|---|---|---|---|---|
| T2.1 | The repository follows the kit standard 0.0.54 | `docs/plans/execution/`, `docs/operations/documentation-plan.md`, `docs/operations/proposals.md`, `packages/js/tests`, `config/layout.yml`, `Makefile`, `.github/workflows/gates.yml`, `config/owner-checks.json` | `make kit-check` | [o] |
| T2.2 | The packages keep no AGENTS, CHANGELOG or Makefile: their sections merge into the root AGENTS and CHANGELOG, their checks are targets of the root Makefile, the layout exception is removed, the PHP platform of the Composer manifests is 8.4.1 with the locks locked again, the recipes that the Makefile lost are restored, and the comparison product is no longer named | `AGENTS.md`(.ko), `CHANGELOG.md`(.ko), `Makefile`, `config/layout.yml`, `composer.json`, `composer.lock`, `packages/php/composer.json`, `packages/php/composer.lock`, `packages/php-ext/composer.json`, `packages/php-ext/composer.lock`, `packages/*/README.md`(.ko), `docs/plans/execution/checklist.md`(.ko) | `make kit-check` and `node node_modules/@polyspec/kit/dist/run-tests.mjs node -- tests/scripts/environment.test.mts` | [o] |

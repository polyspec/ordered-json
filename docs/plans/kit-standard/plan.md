<!-- doc-id: plan-kit-standard -->
# Kit standard

[한국어](plan.ko.md)

## Prerelease reconsideration

The review before 0.0.10 distinguishes completed work, superseded requirements, conditional withdrawals and work that still needs evidence. A historical withdrawal does not exempt a task from this review.

| Item | Review decision | Remaining condition |
| --- | --- | --- |
| T2.56 | Its Go error-handling scope is covered by completed T2.57. Keep the consolidation record. | Reopen only for a new error-handling defect. |
| T2.65 | Retain the Composer archive consumer required by [artifact proof](../../operations/distribution.md#tag-release). The request to replace artifact verification with source installation is retired. | Consumer installation must pass on the actual packaged ZIP. |
| T2.66 | Retain the npm tarball consumer required by the same artifact proof. Development source links have a different scope. The replacement request is retired. | Consumer installation must pass on the actual tarball. |
| T2.79 | The report test reads the sibling kit.mk that the Makefile includes; all 20 owning workflow tests pass. | None for this path correction. |
| T2.80 | The original withdrawal was conditional on the absence of a CI plan. The [execution plan](../execution/plan.md) now exists, and T2.80-1 tracks adoption of the shared fixes. | Integrate the kit patch set and adopt its canonical workflows. |
| T2.48 | A benchmark measured under heavy concurrent load is not reliable performance evidence. Keep the existing result without claiming a successful remeasurement. | Use a clean checkout when the load average is below 2, run make benchmark, commit its generated result and run make benchmark-check. |
| T2.67 | The final hosted run remains required after the integration and record updates. | The final main revision must pass the hosted checks. |

### Prepared kit patch set

The isolated kit branch `fix/release-bootstrap-K614-1` contains only the fixes prepared for the observed failures:

- K614-1: prepare and build sibling kit before consumer release commands. Nine owning workflow tests pass.
- K614-1-1: preserve the configured PHP CLI extensions for arginfo generation, including dynamically loaded tokenizer. Its reproduction fails before the fix and passes after it.
- K614-1-2: fetch shared Rust checker crates during installation before offline gates. Its setup-order reproduction fails before the fix and passes after it.

TypeScript compilation and document checks pass on the patch set. These are local preparation results; they do not establish that kit main contains the fixes or that the remote aggregate passes. Preserve other active kit workspaces and their uncommitted changes.

### Steps before publication

1. Adopt published kit 0.0.56 and its canonical workflows. Its installed-package bootstrap supersedes the prepared sibling-checkout workaround; the old patch branch remains historical preparation.
2. Keep the package manifests, consumer manifests and locks at the requested version. Build preview archives from a clean committed tree and inspect their manifests and file lists; the publishing workflow rebuilds the final assets from its tag.
3. Complete T2.48 only with a valid clean measurement under its stated load condition. Never edit timing data or source state to satisfy the check.
4. Obtain successful hosted evidence for the final revision, then complete T2.67 with that evidence. Creating tags and publishing are later steps, not evidence of local preparation.

## Adoption of kit 0.0.56

The published provider supplies an installed-package bootstrap and canonical workflows. T2.80-1 adopts its exact archive and integrity through the native npm lock, syncs its declared copies, and moves the consumer Makefile and repository-owned CI to the installed bootstrap. CI installs the locked package before its first make command; development source links remain native npm state. The consumer installer fetches the published Rust catch-checker dependencies before offline linting. Final aggregate evidence remains T2.67, and a valid benchmark remains T2.48.

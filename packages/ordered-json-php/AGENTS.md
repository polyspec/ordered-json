<!-- doc-id: php-development -->
# Development procedure

[한국어](AGENTS.ko.md)

<a id="contract"></a>
## Contract and documentation

Read [usage](README.md) and the shared JSON contract of the repository before editing. Update the common specification before a behavior change. Official cases and expected results belong to the repository root. Keep this package free of independent goldens.

English is canonical. Update paired Korean documents with the same information and review the complete translation before updating its `source-sha256`. `make documents-check` of the repository root reads every Markdown document (`config/documents.json`). Keep private preferences, conversation context, credentials, and backup locations outside Git. Use direct factual comments and commit messages.

<a id="checks"></a>
## Required checks

The required checks of `AGENTS.md` at the repository root apply to this package. Development runs unit tests only: while a change is in progress, run the RED case and then the same case to GREEN. The commands of this directory are end-to-end checks; hosted CI runs the full suite after the push, and no rule requires a local run before a commit or a push:

~~~sh
make check
make docs-check
git diff --check
~~~

`make check` runs the shared verifier for this package alone (`scripts/verify.py --only`) and writes no record; `make docs-check` runs `make documents-check` of the repository root. The implementation registry `implementations.json` at the repository root declares the build, package test, and adapter commands of this package. The full suite of the repository root runs `cargo clippy --all-targets -- -D warnings` in `packages/ordered-json-rust/` and `go vet ./...` in `packages/ordered-json-go/`. Native source changes require a new build; the shared native check rebuilds automatically.

<a id="completion"></a>
## Completion

Include documentation and changelog changes with behavior changes. Verify source publication separately from tests.

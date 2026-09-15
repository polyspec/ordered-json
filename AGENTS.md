<!-- doc-id: development -->
# Development procedure

[한국어](AGENTS.ko.md)

<a id="workflow"></a>
## Required workflow

Read [documentation management](docs/documentation-plan.md), the relevant [specification](docs/spec/json-contract.md), and [feature state](docs/features.md) before editing. Update the specification before a behavior change. Mark incomplete work in the feature record.

Keep correct code and factual history. Explain actual causes directly. Include affected documentation, feature state, and changelog entries with code changes. Keep personal preferences, conversation context, credentials, and backup locations outside Git.

English is canonical. Update the paired Korean document with the same information. Update its `source-sha256` only after comparing the complete translation. Use direct technical language with explicit subjects and operations in documentation, comments, commit messages, and translations.

Do not infer authorization to send messages, publish artifacts, change access controls, or rewrite history. Follow authorization already provided for the task. Do not delegate to sub-agents unless the user or applicable instructions explicitly request delegation.

<a id="verification"></a>
## Required checks

Each implementation package owns its source and document manifest. Run these commands from the repository root:

~~~sh
make check
git diff --check
~~~

For full supplementary coverage:

~~~sh
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

Run `make docs-check` for documentation-only review. When sources change and a PIE record exists, run `make pie-check PIE=/path/to/pie.phar` with the applicable supplementary suite first, then run `make check` to generate a current record; the documentation check in `make check` rejects a stale PIE record. Do not edit verification results or source hashes to make checks pass.

The [implementation registry](implementations.json) declares package paths, build, adapter, and runtime commands. Add new languages there and in a package directory without changing the shared JSON comparison algorithm. A contract change updates the verifier and affected packages in one repository revision. See the [repository contract](docs/spec/repositories.md).

All language adapters use [official.json](examples/official.json) and [scripts/verify.py](scripts/verify.py). Add shared cases there or under `fixtures/`. Do not create separate language-specific examples or expected results.

When Rust code changes, run `cargo clippy --all-targets -- -D warnings` in `rust/`. When Go code changes, run `go vet ./...` in `go/`. Rebuild the PHP extension when native code changes. Never treat old binaries or prior results as verification of changed code.

<a id="completion"></a>
## Completion

Review code and tests to confirm documentation accuracy. Automated link, revision, and status checks do not establish prose accuracy. Check actual publication separately from tests and update [distribution status](docs/operations/distribution.md) only with observed evidence.

Keep Git messages factual and concise. Separate unrelated changes where possible. Update private memory outside Git before completing the task.

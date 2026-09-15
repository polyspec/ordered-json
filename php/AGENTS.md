<!-- doc-id: development -->
# Development procedure

[한국어](AGENTS.ko.md)

<a id="contract"></a>
## Contract and documentation

Read [usage](README.md) and the shared JSON contract in the root repository before editing. Update the common specification before a behavior change. Official cases and expected results belong in the root repository. Keep this package free of independent goldens.

English is canonical. Update paired Korean documents with the same information and review the complete translation before updating its `source-sha256`. Register documents in [the manifest](docs/documentation-manifest.json). Keep private preferences, conversation context, credentials, and backup locations outside Git. Use direct factual comments and commit messages.

<a id="checks"></a>
## Required checks

~~~sh
make check
make docs-check
git diff --check
~~~

Run the shared check against the current candidate before a PR or source publication. Use the supplementary suite when available. When Rust code changes, also run `cargo clippy --all-targets -- -D warnings`; when Go code changes, run `go vet ./...`. Native source changes require a new build; the shared native check rebuilds automatically.

The root registry defines this package's verifier command. The aggregate result covers all packages at the same repository revision. Test and publication state must be recorded separately. Current hosted CI is not configured; the commands above are required before publication.

<a id="completion"></a>
## Completion

Include documentation and changelog changes with behavior changes. Verify source publication separately and update relevant private memory outside Git. Follow existing task authorization. Do not delegate to sub-agents unless explicitly requested. Do not rewrite existing history without explicit authorization.

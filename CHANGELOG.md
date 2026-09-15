<!-- doc-id: changelog -->
# Changelog

[한국어](CHANGELOG.ko.md)

<a id="unreleased"></a>
## Unreleased — 2026-09-07

- Documented running `make pie-check` before `make check` after source changes, because the documentation check rejects a stale PIE record.
- Reduced per-value parser and serializer work in every implementation without changing results, errors, or offsets. JavaScript checks values with a private-field brand instead of a `WeakSet` registry, slices unescaped strings from the source, and creates object key tokens on access. Go allocates values in chunks and decodes string units on access. Rust stores kind-specific payloads instead of an empty hash map, item vector, and unit vector per value. The PHP library and extension use an integer descriptor tape, and the extension validates UTF-8 while scanning strings instead of in a separate pass. Values without insignificant whitespace or duplicate keys serialize by copying their source token. Differential tests compared parse results, errors, offsets, accessors, factories, and serialization with the previous implementations. The PHP descriptor format is described in the [API contract](docs/spec/api.md#php).
- Fixed benchmark execution to use Rust release builds, fixed workload input digests, repeated samples, median/p95 statistics, environment fingerprints, and committed results.
- Preserved the committed benchmark baseline when a comparable run exceeds its tolerance and recorded failed measurements separately for review.
- Corrected the native macOS deployment target and bundle configuration to remove the obsolete `-single_module` and `-undefined suppress` linker warnings.
- Published five independent implementation repositories with their existing source histories and replaced common implementation directories with pinned submodules.
- Added standalone candidate checks using a pinned common verifier and explicit test dependency commits.
- Added PIE artifact verification using the same shared JSON cases and separate PHP and extension version records.
- Updated the Go module to `github.com/polyspec/ordered-json/go`.
- Added `make distclean` before repeated native setup because moved dependency files retained the previous build path.
- Added a registry of implementation build, adapter, and runtime commands and a shared standalone verification entry point.
- Separated PHP extension sources into `php-extension/src` and added PIE package metadata with a default-enabled standalone build.
- Removed host JSON parser and serializer dependencies from core value construction and string handling, and added shared repeated round-trip verification across all implementations.
- Added reproducible cross-language performance benchmarks against runtime-native JSON APIs.
- Added a fixed workload manifest and strict benchmark row, input-size, and output-size checks.
- Removed native PHP extension re-parsing during serialization and reduced repeated ordered-map lookups in the Go and Rust implementations.
- Optimized JavaScript serialization and Unicode escape parsing, lazily hydrated PHP descriptor children, removed avoidable Rust serializer cache allocations, and added the explicit zero-copy Go `ParseBytesBorrowed` API.
- Set the unreleased package and extension version to `0.0.1`; no release or automation is configured.

- Renamed language packages, namespaces, imports, native symbols, and build outputs to the ordered-json identifiers in the [API contract](docs/spec/api.md).
- Added English canonical documents and paired Korean translations for specifications, APIs, feature state, operations, examples, and development procedure.
- Added `make check` and `make docs-check`. Checks validate document registration, links, translation revisions, section/code parity, feature state, and current verification evidence. Verification records now include the actual source hashes, runtime versions, and common test results.
- Rebuild the PHP extension from clean phpize outputs because copied read-only build files prevented repeated setup. Build error diagnostics now stop verification even when the tool returns a zero exit status.
- Moved the requested ojson comparison into `docs/reports/` and normalized compiler diagnostic paths to source-relative paths.
- Changed JSON objects to ordered associative maps. Duplicate keys now overwrite the value while retaining the first key position, so each decoded key has one value. Removed the duplicate lookup and member-list APIs. Default serialization now emits the associative object; source inspection remains available separately.
- Added JavaScript, Rust, Go, pure PHP, and PHP extension implementations with strict parsing, recursive document order, exact number tokens, and construction APIs.
- Centralized official inputs and expected results in [official.json](examples/official.json), with shared grammar fixtures and optional supplementary inputs.
- Verified fresh independent clones and the aggregate submodule checkout with 433 shared cases per implementation. The PIE-built artifact also passed all 433 cases; 42 checker tests passed. That earlier run recorded two PHP build-tool linker deprecation warnings in its [verification record](https://github.com/polyspec/ordered-json/blob/main/docs/verification.json).

The current [verification record](docs/verification.json) identifies the tested source and results for all five implementations and the documentation checker tests. [Distribution observations](docs/distribution.json) are separate. This entry records development changes and does not declare a package release.

<!-- doc-id: changelog -->
# Changelog

[한국어](CHANGELOG.ko.md)

<a id="unreleased"></a>
## Unreleased — 2026-09-07

- Every package reports its public symbols, and the standard names the cases that cover each one. The comparison found four gaps: Go `ParseBytesBorrowed` had no test, Rust `OrderedMap::iter` and `stringify` were never called by a case, and the JavaScript type declaration described a `stringify` options argument the function does not take.
- The shared check compares where each implementation rejects an input, and every implementation now reports the first byte that makes the document invalid. The comparison found five documents whose positions differed: JavaScript, Go and both PHP backends pointed one byte past an unescaped control character, and pure PHP pointed at the start of an invalid Unicode escape instead of the offending byte.
- Added a package test standard and the check that enforces it. Each implementation reports the cases it runs, and `make check` fails when a required case is missing or a reported case is not declared, so cross-language coverage is decided by the tool rather than by review.
- An invalid UTF-8 error reports the first invalid byte in every implementation. JavaScript and Go reported offset 0 while Rust and both PHP backends reported the byte, and no shared case compared the position. Package tests now require the rule in every implementation.
- The JavaScript package declares its own tests for the value API, which no shared case can reach. Every implementation package now declares package tests.
- The Rust package declares its own tests for the value API, which no shared case can reach.
- Fixed the PHP unpaired-surrogate error, which raised a class-not-found error instead of `UnexpectedValueException` because the exception name was unqualified inside the namespace. The PHP package now declares its own tests, which found it.
- The PHP extension package declares its own tests for the descriptor API, which no shared case can reach.
- The API contract states the rule for an API that only one binding provides: it uses the shared parser and serializer, leaves results, errors, and offsets unchanged, appears in the binding extensions section, and is covered by its package's declared tests. Go `Marshal` is documented there.
- The implementation registry declares each package's own test command, `make check` runs the declared commands, and the verification record requires their results. Shared cases run through adapters and cannot reach a language-specific API, so a defect in one survived while every shared case passed.
- Corrected Go `Marshal` omission rules and error reporting: `omitempty` and `omitzero` are separate rules, non-finite floats name the field that holds them, and the unreachable `time.Time` branch is removed. A seeded randomized test compares 20,000 values with the host encoder's decoded structures.
- Fixed Go `Marshal`: anonymous struct fields contributed no fields, a repeated field name silently lost a field, and a cyclic value recursed until the process died. Promotion now matches Go field promotion, repeated names and values deeper than the parser's limit are errors.
- PHP object hydration creates one value per member instead of two; serialization reads key tokens from the descriptor. Parse followed by full traversal took 0.85-0.99 of the previous time with the extension and 0.90-1.00 in pure PHP, with identical results.
- Added the Go `Marshal` binding for typed struct, map, slice, scalar, time and byte values. It validates custom marshaler output through ordered-json and produces compact JSON without using the host JSON encoder.
- Kept PHP container serialization out of `compact()`, whose larger call frame had made extension stringify about 1ns slower after the accessor changes. Extension stringify now takes 0.92-0.95 of the time before those changes.
- The PHP extension creates child `Value` objects in C with `ordered_json_hydrate()` instead of a PHP loop. Parse followed by full traversal took 0.65-0.99 of the previous time with the extension; parse, stringify, and round trip stayed within 0.99-1.02, with identical results.
- Rust root arrays take the parser's pending item stack instead of copying every item, releasing spare capacity above one quarter of the length. Parsing root arrays of 90 and 110,000 numbers took 0.84-0.85 of the previous time, with identical results.
- Reduced PHP value access cost: accessors read the descriptor tape directly instead of chaining helper calls, child values are created without a promoted constructor, and escaped strings decode to UTF-8 without an intermediate UTF-16 unit array. Parse followed by full traversal took 0.43-0.89 of the previous time with the extension and 0.60-0.97 in pure PHP, with identical results.
- Stopped freezing JavaScript `Value` objects during parsing. Values still cannot be modified through the library API because their state is held in private fields; returned item and key arrays remain frozen. The API contract now states this guarantee.
- Removed the PHP `useNative` parse option, `parseNative()`, the unused PHP `stringify()` compact flag, the unused JavaScript `stringify()` options argument, and the native `ordered_json_compact()` function. PHP uses the extension when it is loaded and the pure implementation otherwise.
- Fixed pure PHP UTF-8 validation that rejected valid input under very low PCRE backtrack or recursion limits, and reduced pure PHP parser overhead by passing offsets through local variables.
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

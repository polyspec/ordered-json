<!-- doc-id: performance-benchmarks -->
# Performance benchmarks

`run.py` compares the ordered-json implementation with the conventional JSON
implementation available in each runtime. The benchmark uses the same input
documents, warm-up count, iteration count, and sample count for every
implementation. Rust always uses the release profile.

The benchmark reports parse, stringify, and parse-plus-stringify timings. It
also checks a digest of the produced output so a fast but incorrect ordered-json
implementation is not reported as a valid measurement. Results are
machine-specific. Each measurement stores raw samples, median, p95, input
digests, build profile, runtime fingerprint, and Git commit/working-tree state in
`benchmarks/results.json`.
The result file is committed so the measurement history and exact protocol are
visible in the repository.

Native timings are separate baselines, not claims of equivalent behavior:
standard native APIs generally do not retain object order or exact number
tokens. The ordered-json implementations must agree with each other; native
output digests may differ for those intentional reasons.

`workload.json` is the authority for fixture digests, byte counts, node counts,
scalar counts, maximum depth, warm-up, iterations, samples, and regression
tolerances. The runner rejects changed inputs, missing or duplicate
implementation rows, and incorrect reported input sizes. Output byte counts
remain observable results because native serialization can differ.

Nanosecond values cannot be identical across different machines. A run is
comparable only when its recorded environment fingerprint matches the committed
result. Matching environments allow a 10% median and 30% p95 increase after
taking the median ratio across fixtures for each ordered-json implementation
and metric; this avoids treating one noisy small fixture as a regression. Other
environments are recorded as `not-comparable`. The command writes the current
result unless `--check` is supplied.
When a comparable run exceeds the tolerance, the runner preserves the committed
baseline and writes the failed measurement to `.cache/benchmark.current.json`.
Use `--update-baseline` only after reviewing that measurement; an explicit
baseline update is recorded as `baseline-updated`.

Run from the repository root:

```sh
make benchmark
python3 benchmarks/run.py --check
python3 benchmarks/run.py --update-baseline
python3 benchmarks/run.py --iterations 10000 --warmup 1000 --samples 9
```

The Rust baseline is `serde_json`, because Rust does not provide a JSON parser
in its standard library. The JavaScript, Go, and PHP baselines use their
runtime-native JSON APIs. PHP reports both the pure PHP implementation and the
native extension implementation.

The Go ordered-json benchmark uses the explicit `ParseBytesBorrowed` path. It
avoids copying the fixture bytes, and the benchmark keeps each input buffer
alive and unchanged for the entire measurement. General callers should use
`ParseBytes` when the input buffer may be modified.

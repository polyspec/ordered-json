<!-- doc-id: performance-benchmarks -->
# Performance benchmarks

`run.py` compares the ordered-json implementation with the conventional JSON
implementation available in each runtime. The benchmark uses the same input
documents and iteration count for every implementation.

The benchmark reports parse, stringify, and parse-plus-stringify timings. It
also checks a digest of the produced output so a fast but incorrect ordered-json
implementation is not reported as a valid measurement. Results are
machine-specific and are written to `.cache/benchmark.json`; they are not
committed.

Native timings are separate baselines, not claims of equivalent behavior:
standard native APIs generally do not retain object order or exact number
tokens. The ordered-json implementations must agree with each other; native
output digests may differ for those intentional reasons.

Run from the repository root:

```sh
python3 benchmarks/run.py
python3 benchmarks/run.py --iterations 10000
```

The Rust baseline is `serde_json`, because Rust does not provide a JSON parser
in its standard library. The JavaScript, Go, and PHP baselines use their
runtime-native JSON APIs. PHP reports both the pure PHP implementation and the
native extension implementation.

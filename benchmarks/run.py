#!/usr/bin/env python3
"""Run equal-workload performance comparisons for every implementation."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from registry import prepare, repository_paths

WORKLOAD = json.loads((ROOT / "benchmarks/workload.json").read_text())
if WORKLOAD.get("schema_version") != 2:
    raise SystemExit("Unsupported benchmark workload schema")
PROTOCOL = WORKLOAD["benchmark"]
WORKLOADS = {item["file"]: item for item in WORKLOAD["fixtures"]}
FIXTURES = [ROOT / "benchmarks/fixtures" / name for name in WORKLOADS]
RESULTS = ROOT / "benchmarks/results.json"
CURRENT = ROOT / ".cache/benchmark.current.json"

def validate_workload():
    actual = {path.name for path in (ROOT / "benchmarks/fixtures").glob("*.json")}
    if actual != set(WORKLOADS):
        raise SystemExit(f"Workload manifest does not match fixtures: {sorted(actual ^ set(WORKLOADS))}")
    for name, item in WORKLOADS.items():
        source = (ROOT / "benchmarks/fixtures" / name).read_bytes()
        if len(source) != item["input_bytes"]:
            raise SystemExit(f"Input byte count changed for {name}")
        if hashlib.sha256(source).hexdigest() != item["sha256"]:
            raise SystemExit(f"Input digest changed for {name}")
        required = {"input_bytes", "objects", "arrays", "strings", "numbers", "booleans", "nulls", "nodes", "max_depth", "sha256"}
        if set(item) != required | {"file"}:
            raise SystemExit(f"Invalid workload metadata for {name}")

def command_version(command):
    try:
        return subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.STDOUT).splitlines()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        return "unavailable"

def source_state():
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())}

def environment():
    return {
        "python": sys.version.split()[0],
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "node": command_version(["node", "--version"]),
        "go": command_version(["go", "version"]),
        "php": command_version(["php", "-n", "-v"]),
        "rust": command_version(["rustc", "--version"]),
        "cargo": command_version(["cargo", "--version"]),
        "phpize": command_version(["phpize", "--version"]),
        "php_config": command_version(["php-config", "--version"]),
        "rust_profile": "release",
        "php_ini": "-n",
    }

def run(command, env, cwd=ROOT, label=None):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=True)
    rows = []
    for line in result.stdout.splitlines():
        file, name, parse_ns, stringify_ns, roundtrip_ns, parse_p95, stringify_p95, roundtrip_p95, samples, digest, input_bytes, output_bytes = line.split("\t")
        rows.append({"file": Path(file).name, "implementation": f"{label}:{name}" if label else name,
                     "parse_ns": float(parse_ns), "stringify_ns": float(stringify_ns), "roundtrip_ns": float(roundtrip_ns),
                     "parse_p95_ns": float(parse_p95), "stringify_p95_ns": float(stringify_p95), "roundtrip_p95_ns": float(roundtrip_p95),
                     "samples": json.loads(samples),
                     "sha256": digest, "input_bytes": int(input_bytes), "output_bytes": int(output_bytes)})
    return rows

def compare(previous, current):
    if not previous:
        return {"status": "no-baseline"}
    if previous.get("environment") != current["environment"] or previous.get("protocol") != current.get("protocol"):
        return {"status": "not-comparable", "reason": "environment fingerprint or measurement protocol differs"}
    old = {(row["implementation"], row["file"]): row for row in previous["results"]}
    ordered = {"js:ordered-json", "go:ordered-json", "php:custom", "php-extension:extension", "rust:ordered-json"}
    ratios = {}
    failures = []
    for row in current["results"]:
        if row["implementation"] not in ordered:
            continue
        before = old.get((row["implementation"], row["file"]))
        if before is None:
            failures.append({"key": [row["implementation"], row["file"]], "reason": "missing baseline"})
            continue
        for metric, tolerance in (("parse_ns", PROTOCOL["median_tolerance"]), ("stringify_ns", PROTOCOL["median_tolerance"]),
                                  ("roundtrip_ns", PROTOCOL["median_tolerance"]), ("parse_p95_ns", PROTOCOL["p95_tolerance"]),
                                  ("stringify_p95_ns", PROTOCOL["p95_tolerance"]), ("roundtrip_p95_ns", PROTOCOL["p95_tolerance"])):
            if before[metric] > 0:
                ratios.setdefault((row["implementation"], metric, tolerance), []).append(row[metric] / before[metric])
    for (implementation, metric, tolerance), values in ratios.items():
        values.sort()
        aggregate = values[len(values) // 2]
        if aggregate > 1 + tolerance:
            failures.append({"implementation": implementation, "metric": metric,
                             "aggregate_ratio": aggregate, "tolerance": tolerance, "fixture_ratios": values})
    return {"status": "failed" if failures else "passed", "failures": failures}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--warmup", type=int)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--check", action="store_true", help="measure without replacing the committed result")
    parser.add_argument("--update-baseline", action="store_true", help="replace the committed result after reviewing the measurement")
    args = parser.parse_args()
    iterations = args.iterations or PROTOCOL["iterations"]
    warmup = args.warmup or PROTOCOL["warmup"]
    samples = args.samples or PROTOCOL["samples"]
    if min(iterations, warmup, samples) < 1: parser.error("measurement counts must be positive")
    validate_workload()
    files = [str(path) for path in FIXTURES]
    env = os.environ.copy(); env.update({"OJ_BENCH_ITERATIONS": str(iterations), "OJ_BENCH_WARMUP": str(warmup),
                                         "OJ_BENCH_WARMUP_MS": str(PROTOCOL["warmup_ms"]), "OJ_BENCH_SAMPLES": str(samples)})
    commands = []
    required_tools = {name: shutil.which(name) for name in ("node", "go", "php", "cargo", "phpize", "php-config")}
    missing = [name for name, path in required_tools.items() if path is None]
    if missing: raise SystemExit("Missing benchmark tools: " + ", ".join(missing))
    commands.extend([
        ("js", ROOT, ["node", "benchmarks/js.mjs", *files]),
        ("go", ROOT / "go", ["go", "run", "./internal/benchmark", *files]),
        ("php", ROOT, ["php", "-n", "benchmarks/php.php", "custom", *files]),
        ("php-native", ROOT, ["php", "-n", "benchmarks/php.php", "native-json", *files]),
    ])
    extension = ROOT / "php-extension/src/modules/ordered_json.so"
    prepare(["php-extension"], repository_paths(ROOT), ROOT / ".cache/probes")
    if not extension.is_file(): raise SystemExit("PHP extension benchmark artifact was not built")
    commands.extend([
        ("php-extension", ROOT, ["php", "-n", "-d", f"extension={extension}", "benchmarks/php.php", "extension", *files]),
        ("rust", ROOT, ["cargo", "run", "--release", "--quiet", "--manifest-path", "rust/Cargo.toml", "--example", "benchmark", "--", *files]),
    ])
    rows = []
    for label, cwd, argv in commands:
        rows.extend(run(argv, env, cwd, label))
    ordered = {}
    for row in rows:
        if row["implementation"].endswith(":ordered-json") or row["implementation"] in {"php:custom", "php-extension:extension"}:
            ordered.setdefault(row["file"], set()).add(row["sha256"])
    inconsistent = {file: digests for file, digests in ordered.items() if len(digests) != 1}
    if inconsistent:
        raise SystemExit(f"ordered-json implementations produced different output digests: {inconsistent}")
    expected = {f"{label}:{mode}" for label, mode in (
        ("js", "ordered-json"), ("js", "native-json"), ("go", "ordered-json"),
        ("go", "native-json"), ("php", "custom"), ("php-native", "native-json"),
        ("php-extension", "extension"), ("rust", "ordered-json"), ("rust", "native-json"))}
    actual = {row["implementation"] for row in rows}
    if actual != expected or len(rows) != len(expected) * len(FIXTURES):
        raise SystemExit(f"Benchmark rows are incomplete or duplicated: expected {len(expected) * len(FIXTURES)}, got {len(rows)}")
    for row in rows:
        workload = WORKLOADS[row["file"]]
        if row["input_bytes"] != workload["input_bytes"]:
            raise SystemExit(f"Input byte count mismatch for {row['implementation']}/{row['file']}")
    current_environment = environment()
    previous = json.loads(RESULTS.read_text()) if RESULTS.is_file() else None
    protocol = {"iterations": iterations, "warmup": warmup, "warmup_ms": PROTOCOL["warmup_ms"], "samples": samples,
                "median_tolerance": PROTOCOL["median_tolerance"], "p95_tolerance": PROTOCOL["p95_tolerance"]}
    record = {"schema_version": 2,
              "source": source_state(),
              "protocol": protocol,
              "environment": current_environment, "fixtures": WORKLOAD["fixtures"], "results": rows,
              "comparison": compare(previous, {"environment": current_environment, "protocol": protocol, "results": rows})}
    if args.update_baseline:
        record["comparison"] = {"status": "baseline-updated"}
    if record["comparison"]["status"] == "failed" and not args.update_baseline:
        CURRENT.parent.mkdir(exist_ok=True)
        CURRENT.write_text(json.dumps(record, indent=2) + "\n")
        print(f"Saved failed measurement for review at {CURRENT}")
    elif not args.check:
        RESULTS.write_text(json.dumps(record, indent=2) + "\n")
    for row in rows: print(f"{row['file']:24} {row['implementation']:14} parse={row['parse_ns']:.0f}ns stringify={row['stringify_ns']:.0f}ns")
    print(f"Comparison: {json.dumps(record['comparison'], sort_keys=True)}")
    kept = record["comparison"]["status"] == "failed" and not args.update_baseline
    print(f"{'Kept' if kept else 'Checked' if args.check else 'Saved'} {RESULTS}")
    if record["comparison"]["status"] == "failed" and not args.update_baseline:
        raise SystemExit("benchmark regression exceeded the documented tolerance")

if __name__ == "__main__": main()

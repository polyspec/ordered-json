#!/usr/bin/env python3
"""Run equal-workload performance comparisons for every implementation."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from registry import prepare, repository_paths

WORKLOAD = json.loads((ROOT / "benchmarks/workload.json").read_text())
if WORKLOAD.get("schema_version") != 1:
    raise SystemExit("Unsupported benchmark workload schema")
WORKLOADS = {item["file"]: item for item in WORKLOAD["fixtures"]}
FIXTURES = [ROOT / "benchmarks/fixtures" / name for name in WORKLOADS]

def validate_workload():
    actual = {path.name for path in (ROOT / "benchmarks/fixtures").glob("*.json")}
    if actual != set(WORKLOADS):
        raise SystemExit(f"Workload manifest does not match fixtures: {sorted(actual ^ set(WORKLOADS))}")
    for name, item in WORKLOADS.items():
        source = (ROOT / "benchmarks/fixtures" / name).read_bytes()
        if len(source) != item["input_bytes"]:
            raise SystemExit(f"Input byte count changed for {name}")
        required = {"input_bytes", "objects", "arrays", "strings", "numbers", "booleans", "nulls", "nodes", "max_depth"}
        if set(item) != required | {"file"}:
            raise SystemExit(f"Invalid workload metadata for {name}")

def run(command, env, cwd=ROOT, label=None):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=True)
    rows = []
    for line in result.stdout.splitlines():
        file, name, parse_ns, stringify_ns, roundtrip_ns, digest, input_bytes, output_bytes = line.split("\t")
        rows.append({"file": Path(file).name, "implementation": f"{label}:{name}" if label else name,
                     "parse_ns": float(parse_ns), "stringify_ns": float(stringify_ns),
                     "roundtrip_ns": float(roundtrip_ns) if roundtrip_ns else None,
                     "sha256": digest, "input_bytes": int(input_bytes), "output_bytes": int(output_bytes)})
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    if args.iterations < 1: parser.error("--iterations must be positive")
    validate_workload()
    files = [str(path) for path in FIXTURES]
    env = os.environ.copy(); env["OJ_BENCH_ITERATIONS"] = str(args.iterations)
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
        ("rust", ROOT, ["cargo", "run", "--quiet", "--manifest-path", "rust/Cargo.toml", "--example", "benchmark", "--", *files]),
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
    output = ROOT / ".cache/benchmark.json"; output.parent.mkdir(exist_ok=True)
    record = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "iterations": args.iterations, "fixtures": WORKLOAD["fixtures"], "results": rows,
              "native_comparison": "baseline-only; native output need not match ordered-json"}
    output.write_text(json.dumps(record, indent=2) + "\n")
    for row in rows: print(f"{row['file']:24} {row['implementation']:14} parse={row['parse_ns']:.0f}ns stringify={row['stringify_ns']:.0f}ns")
    print(f"Saved {output}")

if __name__ == "__main__": main()

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

FIXTURES = sorted((ROOT / "benchmarks/fixtures").glob("*.json"))

def run(command, env, cwd=ROOT, label=None):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=True)
    rows = []
    for line in result.stdout.splitlines():
        file, name, parse_ns, stringify_ns, roundtrip_ns, digest = line.split("\t")
        rows.append({"file": Path(file).name, "implementation": f"{label}:{name}" if label else name,
                     "parse_ns": float(parse_ns), "stringify_ns": float(stringify_ns),
                     "roundtrip_ns": float(roundtrip_ns) if roundtrip_ns else None,
                     "sha256": digest})
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    if args.iterations < 1: parser.error("--iterations must be positive")
    files = [str(path) for path in FIXTURES]
    env = os.environ.copy(); env["OJ_BENCH_ITERATIONS"] = str(args.iterations)
    commands = []
    if shutil.which("node"): commands.append(("js", ROOT, ["node", "benchmarks/js.mjs", *files]))
    if shutil.which("go"): commands.append(("go", ROOT / "go", ["go", "run", "./internal/benchmark", *files]))
    if shutil.which("php"): commands.extend([
        ("php", ROOT, ["php", "-n", "benchmarks/php.php", "custom", *files]),
        ("php-native", ROOT, ["php", "-n", "benchmarks/php.php", "native-json", *files]),
    ])
    extension = ROOT / "php-extension/src/modules/ordered_json.so"
    if shutil.which("phpize") and shutil.which("php-config"):
        prepare(["php-extension"], repository_paths(ROOT), ROOT / ".cache/probes")
        extension = ROOT / "php-extension/src/modules/ordered_json.so"
    if extension.is_file() and shutil.which("php"):
        commands.append(("php-extension", ROOT, ["php", "-n", "-d", f"extension={extension}",
                                                  "benchmarks/php.php", "extension", *files]))
    if shutil.which("cargo"):
        commands.append(("rust", ROOT, ["cargo", "run", "--quiet", "--manifest-path", "rust/Cargo.toml", "--example", "benchmark", "--", *files]))
    if not commands: raise SystemExit("No supported runtime found")
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
    output = ROOT / ".cache/benchmark.json"; output.parent.mkdir(exist_ok=True)
    record = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "iterations": args.iterations, "fixtures": [Path(f).name for f in files], "results": rows}
    output.write_text(json.dumps(record, indent=2) + "\n")
    for row in rows: print(f"{row['file']:24} {row['implementation']:14} parse={row['parse_ns']:.0f}ns stringify={row['stringify_ns']:.0f}ns")
    print(f"Saved {output}")

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""Run one lint that AGENTS requires on the tracked sources.

    python3 scripts/lint.py clippy   cargo clippy --locked --all-targets -- -D warnings in rust/
    python3 scripts/lint.py go-vet   go vet ./... in go/

make check runs each lint as a target of its own after the verification, so hosted CI runs them on every pull
request and every push to main, and make clippy and make go-vet run one. The tools are the pinned ones (make toolchain-check) and run
offline. cargo builds into a target directory of this run, which is removed when the run ends, so no target
directory of another checkout or run decides the result. A lint prints its output as it arrives and fails with
its command, its directory and its exit status; it has no time limit.
"""
import os
from pathlib import Path
import sys
import tempfile

from registry import ROOT, run_streamed

LINTS = {
    'clippy': ('rust', ['cargo', 'clippy', '--locked', '--all-targets', '--', '-D', 'warnings']),
    'go-vet': ('go', ['go', 'vet', './...']),
}


def main(argv):
    if len(argv) != 1 or argv[0] not in LINTS:
        print(f"unknown lint {' '.join(argv) or '(none)'}; the lints are {', '.join(LINTS)}", file=sys.stderr)
        return 2
    name = argv[0]
    folder, command = LINTS[name]
    with tempfile.TemporaryDirectory(prefix=f'ordered-json-{name}-') as target:
        process = run_streamed(name, command, Path(ROOT) / folder, env=dict(os.environ, CARGO_TARGET_DIR=target))
    if process.returncode:
        print(f"{name}: {' '.join(command)} in {folder}/ failed with exit {process.returncode}", flush=True)
        return 1
    print(f"{name}: {' '.join(command)} in {folder}/ passed", flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

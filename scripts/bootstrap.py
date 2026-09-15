#!/usr/bin/env python3
"""Load the common verifier at the revision declared by this checkout."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', type=Path, help='Use an explicit local verifier checkout')
    args, remaining = parser.parse_known_args()
    pin = json.loads((root / 'conformance.json').read_text())['harness']
    if pin.get('url') != 'https://github.com/polyspec/ordered-json.git' or not re.fullmatch(r'[a-f0-9]{40}', pin.get('revision', '')):
        raise ValueError('The common verifier requires its expected URL and a full commit ID')
    harness = args.harness.resolve() if args.harness else root / '.cache/harness' / pin['revision']
    if not args.harness:
        if not (harness / '.git').exists():
            harness.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'init', '--quiet', str(harness)], check=True)
        head = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=harness,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if head.returncode:
            subprocess.run(['git', 'fetch', '--quiet', '--depth=1', pin['url'], pin['revision']], cwd=harness, check=True)
            subprocess.run(['git', 'checkout', '--quiet', '--detach', 'FETCH_HEAD'], cwd=harness, check=True)
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=harness, text=True).strip()
        if actual != pin['revision'] or subprocess.check_output(['git', 'status', '--porcelain'], cwd=harness):
            raise ValueError('The cached common verifier is modified or has the wrong revision')
    command = [sys.executable, str(harness / 'scripts/standalone.py'), '--root', str(root)]
    if args.harness:
        command.append('--local-harness')
    return subprocess.call(command + remaining, cwd=root)


if __name__ == '__main__':
    sys.exit(main())

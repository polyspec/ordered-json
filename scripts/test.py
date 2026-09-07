#!/usr/bin/env python3
"""Run the same ordered JSON contract against all five implementations."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--suite', type=Path, help='Optional checkout of nst/JSONTestSuite')
parser.add_argument('--build-extension', action='store_true', help='Build the PHP extension locally first')
args = parser.parse_args()
env = os.environ.copy()
if args.suite:
    suite = args.suite.resolve()
    if not (suite / 'test_parsing').is_dir():
        parser.error('--suite must contain test_parsing/')
    env['JSON_TEST_SUITE'] = str(suite)

def run(command, cwd=ROOT):
    subprocess.run(command, cwd=cwd, env=env, check=True)

extension = ROOT / 'php/ext/modules/ordered_json.so'
if args.build_extension:
    run(['phpize'], ROOT / 'php/ext')
    run(['./configure', '--enable-ordered-json'], ROOT / 'php/ext')
    run(['make', '-j2'], ROOT / 'php/ext')
if not extension.is_file():
    parser.error('Build the PHP extension with --build-extension first')

command = [os.sys.executable, str(ROOT / 'scripts/verify.py')]
if args.suite:
    command += ['--suite', str(args.suite.resolve())]
run(command)

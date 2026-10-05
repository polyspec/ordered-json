"""The ojson comparison streams its build and judges each probe case by its own deadline."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compare_ojson

# A stand-in for erl: the compile step, the runtime version query and the probe.
ERL = '''#!{python}
import sys, time
arguments = sys.argv[1:]
if 'ojson_comparison' in arguments:
    for line in sys.stdin:
        time.sleep({probe})
        print('{{"ok": false, "decode_error": "fixture"}}', flush=True)
elif 'system_version' in arguments[-1]:
    print('Erlang fixture', end='')
else:
    time.sleep({compile})
    print('src/fixture.erl:1: Warning: fixture warning', flush=True)
'''
# A stand-in for the PyPI ojson module, slowed per case like the Erlang probe.
OJSON = '''import json, time
def loads(source):
    time.sleep({probe})
    return json.loads(source)
def dumps(value):
    return json.dumps(value)
'''


def limited(run):
    """subprocess.run with any time limit the caller passes cut to 1 s."""
    def call(*arguments, **options):
        if 'timeout' in options:
            options['timeout'] = 1
        return run(*arguments, **options)
    return call


class ComparisonRuns(unittest.TestCase):
    def compare(self, compile_seconds, probe_seconds):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            erl = root / 'erl'
            erl.write_text(ERL.format(python=sys.executable, compile=compile_seconds, probe=probe_seconds))
            erl.chmod(0o755)
            package = root / 'ojson-0.1.0'
            (package / 'ojson').mkdir(parents=True)
            (package / 'ojson/ojson.py').write_text(OJSON.format(probe=probe_seconds))
            (package / 'ojson/__init__.py').write_text('from .ojson import loads, dumps\n')
            (package / 'PKG-INFO').write_text('Metadata-Version: 1.0\nName: ojson\nVersion: 0.1.0\n')
            source = root / 'erlang-ojson'
            (source / 'src').mkdir(parents=True)
            subprocess.run(['git', 'init', '-q', str(source)], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=fixture', '-c', 'user.email=fixture@invalid',
                            'commit', '-q', '--allow-empty', '-m', 'fixture'], check=True)
            report = root / 'report.json'
            output = io.StringIO()
            arguments = ['compare_ojson.py', '--python-package', str(package), '--erlang-source', str(source),
                         '--erl', str(erl), '--output', str(report)]
            with patch.object(sys, 'argv', arguments), redirect_stdout(output), \
                    patch('compare_ojson.subprocess.run', limited(subprocess.run)):
                compare_ojson.main()
            return output.getvalue(), json.loads(report.read_text())

    def test_a_silent_erlang_build_runs_past_any_limit_to_its_exit(self):
        log, report = self.compare(2, 0)
        self.assertRegex(log, r'erlang compile: start\n'
                              r'erlang compile: src/fixture\.erl:1: Warning: fixture warning\n'
                              r'erlang compile: exit 0 after \d+ ms\n')
        self.assertEqual(report['erlang_package']['compile_warnings'],
                         'src/fixture.erl:1: Warning: fixture warning\n')

    def test_a_slow_probe_run_is_judged_case_by_case(self):
        log, report = self.compare(0, 0.02)
        for project in ('pypi-ojson', 'erlang-ojson'):
            cases = report['projects'][project]['cases']
            self.assertGreater(len(cases), 50)
            for case in cases:
                self.assertRegex(log, rf'{project}: {re.escape(case["case"])} '
                                      rf'(accepted|rejected) \(\d+ ms\)\n')


if __name__ == '__main__':
    unittest.main()

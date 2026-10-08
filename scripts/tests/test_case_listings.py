"""Case listings are read in a declared machine format, and tool notices on stderr are not failures.

The listing parser skipped lines by their text (`ok`, `?`, `running`, `test result:`), so a change of
a tool's human-readable output could hide a case or add one.
"""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry import REGISTRY
from verify import STANDARD, compare_package_cases

PACKAGE = 'github.com/polyspec/ordered-json/go'


def required(language):
    cases = {case['id'] for case in STANDARD['cases'] if language not in case.get('exemptions', {})}
    return sorted(cases | {case['id'] for case in STANDARD['package_cases'][language]})


def go_name(identifier):
    return 'Test' + ''.join(part.capitalize() for part in identifier.split('_'))


class CaseListings(unittest.TestCase):
    def listing(self, language, form, stdout, stderr='', status=0):
        """A declared listing whose command prints stdout and stderr and exits with status."""
        script = (f'import sys; sys.stdout.write({stdout!r}); sys.stderr.write({stderr!r}); sys.exit({status})')
        entry = {'cwd': tempfile.gettempdir(), 'command': [sys.executable, '-c', script], 'format': form}
        output = io.StringIO()
        with redirect_stdout(output):
            compare_package_cases({language: entry}, [language])
        return output.getvalue()

    def go_events(self, names, extra=()):
        events = [{'Action': 'start', 'Package': PACKAGE}]
        events += [{'Action': 'output', 'Package': PACKAGE, 'Output': name + '\n'} for name in names]
        events += list(extra)
        events += [{'Action': 'output', 'Package': PACKAGE, 'Output': f'ok  \t{PACKAGE}\t0.2s\n'},
                   {'Action': 'pass', 'Package': PACKAGE}]
        return ''.join(json.dumps(event) + '\n' for event in events)

    def test_the_registry_declares_a_format_for_every_listing(self):
        formats = {name: implementation['test_cases'].get('format')
                   for name, implementation in REGISTRY['implementations'].items()}
        self.assertEqual(formats, {'js': 'lines', 'rust': 'cargo-terse', 'go': 'go-test-json', 'php': 'lines',
                                   'php-extension': 'lines', 'python': 'lines'})
        self.assertIn('-json', REGISTRY['implementations']['go']['test_cases']['command'])
        self.assertEqual(REGISTRY['implementations']['rust']['test_cases']['command'][-2:], ['--format', 'terse'])

    def test_go_events_list_the_cases_of_each_package(self):
        self.assertIn('package test cases match the standard',
                      self.listing('go', 'go-test-json', self.go_events([go_name(case) for case in required('go')])))

    def test_a_go_output_that_is_not_a_test_or_its_package_summary_fails(self):
        extra = [{'Action': 'output', 'Package': PACKAGE, 'Output': 'running 3 tests\n'},
                 {'Action': 'output', 'Package': PACKAGE, 'Output': 'ok  \tgithub.com/other/module\t0.1s\n'}]
        with self.assertRaises(RuntimeError) as raised:
            self.listing('go', 'go-test-json', self.go_events([go_name(case) for case in required('go')], extra))
        self.assertIn('running 3 tests', str(raised.exception))
        self.assertIn('github.com/other/module', str(raised.exception))

    def test_cargo_terse_lists_tests_and_rejects_other_lines(self):
        names = ''.join(f'{case}: test\n' for case in required('rust'))
        self.assertIn('package test cases match the standard',
                      self.listing('rust', 'cargo-terse', names + 'speed: benchmark\n'))
        with self.assertRaises(RuntimeError) as raised:
            self.listing('rust', 'cargo-terse', names + '3 tests, 0 benchmarks\n')
        self.assertIn('3 tests, 0 benchmarks', str(raised.exception))

    def test_a_package_list_line_must_be_a_case_id(self):
        with self.assertRaises(RuntimeError) as raised:
            self.listing('js', 'lines', ''.join(case + '\n' for case in required('js')) + 'ok fixture\n')
        self.assertIn('ok fixture', str(raised.exception))

    def test_a_tool_notice_on_stderr_is_printed_and_does_not_fail_the_listing(self):
        printed = self.listing('js', 'lines', ''.join(case + '\n' for case in required('js')),
                               stderr='(node:1) ExperimentalWarning: fixture notice\n')
        self.assertIn('js case listing notice: (node:1) ExperimentalWarning: fixture notice', printed)
        self.assertIn('package test cases match the standard', printed)

    def test_a_failing_listing_fails_with_its_stderr(self):
        with self.assertRaises(RuntimeError) as raised:
            self.listing('js', 'lines', '', stderr='SyntaxError: fixture\n', status=1)
        self.assertIn('exit 1', str(raised.exception))
        self.assertIn('SyntaxError: fixture', str(raised.exception))


if __name__ == '__main__':
    unittest.main()

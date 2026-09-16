"""Every implementation must run the same package test cases.

The standard lives in package-tests.json. Each implementation declares how to
list the cases it runs, so this check compares declarations with what the suites
actually contain instead of relying on a reading of the sources.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry import IMPLEMENTATIONS, REGISTRY, case_commands, repository_paths

ROOT = Path(__file__).resolve().parents[2]
STANDARD = json.loads((ROOT / 'package-tests.json').read_text(encoding='utf-8'))


def normalized(name):
    """Map a test name from any language to a case id.

    TestFooBar and foo_bar: test both become foo_bar. A run of capitals is one
    word, so TypedJSONContract becomes typed_json_contract rather than
    typed_j_s_o_n_contract.
    """
    name = name.split(':')[0].strip()
    name = re.sub(r'^Test', '', name)
    name = re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', name)
    return name.lower()


def collected_cases(name, paths, cache):
    command = case_commands([name], paths, cache).get(name)
    if command is None:
        return None
    process = subprocess.run(command['command'], cwd=command['cwd'], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if process.returncode:
        raise RuntimeError(f'{name} case listing failed:\n{process.stdout}')
    return {normalized(line) for line in process.stdout.splitlines()
            if line.strip() and not line.startswith(('ok', '?', 'FAIL', 'running', 'test result'))}


class CaseNameMapping(unittest.TestCase):
    def test_names_from_each_language_map_to_one_id(self):
        self.assertEqual(normalized('TestDepthArgumentIsBounded'), 'depth_argument_is_bounded')
        self.assertEqual(normalized('depth_argument_is_bounded: test'), 'depth_argument_is_bounded')
        self.assertEqual(normalized('depth_argument_is_bounded'), 'depth_argument_is_bounded')
        self.assertEqual(normalized('TestMarshalPreservesTypedJSONContract'),
                         'marshal_preserves_typed_json_contract')
        self.assertEqual(normalized('TestParseBytesReportsInvalidUTF8'),
                         'parse_bytes_reports_invalid_utf8')


class PackageConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = repository_paths(ROOT)
        cls.cache = ROOT / '.cache/probes'

    def test_the_standard_is_well_formed(self):
        self.assertEqual(STANDARD.get('schema_version'), 1)
        self.assertEqual(set(STANDARD['package_cases']), set(IMPLEMENTATIONS),
                         'Every implementation lists its package-specific cases, even when empty')
        seen = set()
        for case in STANDARD['cases']:
            identifier = case['id']
            self.assertRegex(identifier, r'^[a-z][a-z0-9_]*$')
            self.assertNotIn(identifier, seen, 'Duplicate case id')
            seen.add(identifier)
            self.assertTrue(case['description'].strip(), 'A case states what it covers: ' + identifier)
            for implementation, reason in case.get('exemptions', {}).items():
                self.assertIn(implementation, IMPLEMENTATIONS, 'Unknown implementation: ' + implementation)
                self.assertTrue(reason.strip(), 'An exemption states its reason: ' + identifier)
            self.assertNotEqual(set(case.get('exemptions', {})), set(IMPLEMENTATIONS),
                                'A case no implementation runs does not belong in the standard: ' + identifier)
        for implementation, extras in STANDARD['package_cases'].items():
            for case in extras:
                self.assertRegex(case['id'], r'^[a-z][a-z0-9_]*$')
                self.assertTrue(case['description'].strip(),
                                f"{implementation}: a package case states what it covers: {case['id']}")
                self.assertNotIn(case['id'], seen,
                                 f"{implementation}: a standard case is not a package case: {case['id']}")

    def test_every_implementation_declares_a_case_listing(self):
        missing = [name for name in IMPLEMENTATIONS
                   if REGISTRY['implementations'][name].get('test_cases') is None]
        self.assertEqual(missing, [], 'These implementations cannot report their package test cases')

    def test_each_implementation_runs_the_standard_cases(self):
        required = {name: {case['id'] for case in STANDARD['cases']
                           if name not in case.get('exemptions', {})}
                    | {case['id'] for case in STANDARD['package_cases'][name]}
                    for name in IMPLEMENTATIONS}
        problems = []
        for name in IMPLEMENTATIONS:
            cases = collected_cases(name, self.paths, self.cache)
            if cases is None:
                problems.append(f'{name}: no case listing command')
                continue
            for identifier in sorted(required[name] - cases):
                problems.append(f'{name}: missing case {identifier}')
            for identifier in sorted(cases - required[name]):
                problems.append(f'{name}: case {identifier} is not declared in the standard')
        self.assertEqual(problems, [], '\n'.join(problems))


if __name__ == '__main__':
    unittest.main()

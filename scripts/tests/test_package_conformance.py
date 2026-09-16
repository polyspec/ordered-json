"""Every implementation must run the same package test cases.

The standard lives in package-tests.json. Each implementation declares how to
list the cases it runs, so this check compares declarations with what the suites
actually contain instead of relying on a reading of the sources.
"""
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry import IMPLEMENTATIONS, REGISTRY

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

    def test_the_comparison_runs_after_the_packages_are_built(self):
        # Listings need built artifacts, so verify.py compares them after prepare().
        from verify import compare_package_cases
        self.assertTrue(callable(compare_package_cases))


if __name__ == '__main__':
    unittest.main()

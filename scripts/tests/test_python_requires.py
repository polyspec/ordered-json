"""The Python support range of the package states the minor release that CI tests (T1.32-2).

CI runs the package only under the pinned interpreter of make install-tools, the minor release of .python-version, so
requires-python of packages/ordered-json-python/pyproject.toml is that minor release and nothing older.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RequiresPython(unittest.TestCase):
    def test_requires_python_is_the_minor_release_of_python_version(self):
        pyproject = (ROOT / 'packages/ordered-json-python/pyproject.toml').read_text()
        declared = re.search(r'^requires-python = "(>=\d+\.\d+)"$', pyproject, re.M)
        self.assertIsNotNone(declared, 'pyproject.toml declares requires-python as ">=<major>.<minor>"')
        minor = (ROOT / '.python-version').read_text().strip()
        self.assertRegex(minor, r'^\d+\.\d+$', '.python-version holds the minor release')
        self.assertEqual(declared.group(1), f'>={minor}',
                         f'requires-python must state the tested minor release of .python-version ({minor})')


if __name__ == '__main__':
    unittest.main()

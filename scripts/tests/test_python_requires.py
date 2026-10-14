"""The Python support range of the package states the minor release that CI tests (T1.32-2).

CI runs the package only under the python of mise.toml, which make install-tools installs, so requires-python of
packages/python/pyproject.toml is its minor release and nothing older.
"""
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RequiresPython(unittest.TestCase):
    def test_requires_python_is_the_minor_release_of_the_mise_python(self):
        pyproject = (ROOT / 'packages/python/pyproject.toml').read_text()
        declared = re.search(r'^requires-python = "(>=\d+\.\d+)"$', pyproject, re.M)
        self.assertIsNotNone(declared, 'pyproject.toml declares requires-python as ">=<major>.<minor>"')
        release = tomllib.loads((ROOT / 'mise.toml').read_text())['tools']['python']
        self.assertRegex(release, r'^\d+\.\d+\.\d+$', 'mise.toml pins an exact Python release')
        minor = '.'.join(release.split('.')[:2])
        self.assertEqual(declared.group(1), f'>={minor}',
                         f'requires-python must state the tested minor release of the python of mise.toml ({minor})')


if __name__ == '__main__':
    unittest.main()

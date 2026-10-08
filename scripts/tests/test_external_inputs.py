"""The external inputs that external-inputs.json pins are installed once, refused with both values when their identity
differs, and named with their fix when a check runs without them."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_pie
import external_inputs as toolchains
import verification as test_runner

ROOT = Path(__file__).resolve().parents[2]


def external_root(folder, phar=b'pie tool', suite=None):
    """A checkout with external-inputs.json that pins the PHAR `phar` and the suite checkout `suite`."""
    root = Path(folder) / 'checkout'
    root.mkdir(parents=True)
    supplementary = {'project': 'nst/JSONTestSuite', 'url': 'https://example.invalid/suite', 'revision': 'a' * 40,
                     'cases': 1, 'inputs_sha256': '0' * 64}
    if suite is not None:
        from verification_record import supplementary_manifest
        supplementary = {**supplementary_manifest(suite), 'url': suite.as_uri()}
    (root / 'external-inputs.json').write_text(json.dumps({
        'schema_version': 1,
        'pie': {'release': '1.4.10', 'url': 'https://github.com/php/pie/releases',
                'phar_sha256': hashlib.sha256(phar).hexdigest()},
        'supplementary': supplementary}))
    return root


class ExternalInputs(unittest.TestCase):
    """make install downloads the PIE PHAR and the supplementary suite that external-inputs.json pins."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)

    def test_the_pinned_phar_is_installed_once(self):
        root = external_root(self.folder)
        fetched = []

        def fetch(url):
            fetched.append(url)
            return b'pie tool'

        with redirect_stdout(io.StringIO()):
            toolchains.install_pie(root, fetch)
            toolchains.install_pie(root, fetch)
        self.assertEqual(fetched, ['https://github.com/php/pie/releases/download/1.4.10/pie.phar'],
                         'the second install is a no-op')
        self.assertEqual((root / '.cache/pie/pie.phar').read_bytes(), b'pie tool')
        self.assertEqual(sorted(path.name for path in (root / '.cache/pie').iterdir()), ['pie.phar'])

    def test_a_phar_with_another_hash_is_refused_with_both_hashes(self):
        root = external_root(self.folder, phar=b'the reviewed phar')
        with self.assertRaises(ValueError) as raised, redirect_stdout(io.StringIO()):
            toolchains.install_pie(root, lambda url: b'another phar')
        self.assertIn(f'expected sha256 {hashlib.sha256(b"the reviewed phar").hexdigest()} (external-inputs.json)',
                      str(raised.exception))
        self.assertIn(f'actual {hashlib.sha256(b"another phar").hexdigest()}', str(raised.exception))
        self.assertFalse((root / '.cache/pie/pie.phar').exists())

    def suite(self, cases):
        """A Git repository with the cases {name: text} in test_parsing, one commit."""
        source = self.folder / 'suite'
        (source / 'test_parsing').mkdir(parents=True, exist_ok=True)
        for name, text in cases.items():
            (source / 'test_parsing' / name).write_text(text)
        git = ['git', '-c', 'user.name=test', '-c', 'user.email=test@example.com', '-c', 'init.defaultBranch=main']
        subprocess.run(git + ['init', '--quiet'], cwd=source, check=True)
        subprocess.run(git + ['add', '.'], cwd=source, check=True)
        subprocess.run(git + ['commit', '--quiet', '-m', 'cases'], cwd=source, check=True)
        return source

    def test_the_pinned_suite_revision_is_installed_once(self):
        source = self.suite({'y_object.json': '{}', 'n_array.json': '['})
        root = external_root(self.folder, suite=source)
        with redirect_stdout(io.StringIO()) as printed:
            toolchains.install_suite(root)
            toolchains.install_suite(root)
        target = root / '.cache/JSONTestSuite'
        self.assertEqual(sorted(path.name for path in (target / 'test_parsing').iterdir()), ['n_array.json', 'y_object.json'])
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=target, check=True, capture_output=True,
                                  text=True).stdout.strip()
        self.assertEqual(revision, json.loads((root / 'external-inputs.json').read_text())['supplementary']['revision'])
        self.assertIn('installed in', printed.getvalue().splitlines()[-1], 'the second install is a no-op')
        self.assertEqual(sorted(path.name for path in target.parent.iterdir()), ['JSONTestSuite'])

    def test_a_suite_with_other_inputs_is_refused_with_both_values(self):
        source = self.suite({'y_object.json': '{}'})
        root = external_root(self.folder, suite=source)
        pin = json.loads((root / 'external-inputs.json').read_text())
        pin['supplementary']['inputs_sha256'] = 'f' * 64
        (root / 'external-inputs.json').write_text(json.dumps(pin))
        with self.assertRaises(ValueError) as raised, redirect_stdout(io.StringIO()):
            toolchains.install_suite(root)
        self.assertIn(f'JSONTestSuite inputs_sha256: expected {"f" * 64}, actual ', str(raised.exception))
        self.assertFalse((root / '.cache/JSONTestSuite').exists())
        self.assertEqual(list((root / '.cache').iterdir()), [], 'the staging checkout is removed')


class MissingExternalInputs(unittest.TestCase):
    """A check runs offline, so an input that make install did not download fails with the advice to run make install."""

    def run_main(self, main, argv):
        errors = io.StringIO()
        with patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()), redirect_stderr(errors):
            try:
                status = main()
            except SystemExit as exit:
                status = exit.code
        return status, errors.getvalue()

    def test_a_missing_phar_names_make_install(self):
        with tempfile.TemporaryDirectory() as folder, patch('check_pie.run_streamed') as pie:
            missing = Path(folder) / 'pie.phar'
            status, errors = self.run_main(check_pie.main, ['check_pie.py', '--pie', str(missing)])
        self.assertEqual(status, 1, errors)
        self.assertIn(f'the PIE PHAR {missing} does not exist; run make install, which downloads the PIE release of '
                      'external-inputs.json into .cache/pie/pie.phar', errors)
        self.assertFalse(pie.called)

    def test_a_missing_suite_names_make_install(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / 'JSONTestSuite'
            phar = Path(folder) / 'pie.phar'
            phar.write_text('<?php\n')
            for main, argv in ((test_runner.main, ['verification.py', '--suite', str(missing)]),
                               (check_pie.main, ['check_pie.py', '--pie', str(phar), '--suite', str(missing)])):
                with self.subTest(command=argv[0]), patch('verification.run_unit_tests') as unit, \
                        patch('check_pie.run_streamed') as pie:
                    status, errors = self.run_main(main, argv)
                    self.assertNotEqual(status, 0, errors)
                    self.assertIn(f'the supplementary suite {missing} has no test_parsing/; run make install, '
                                  'which installs the suite of external-inputs.json into .cache/JSONTestSuite', errors)
                    self.assertFalse(unit.called or pie.called)


if __name__ == '__main__':
    unittest.main()

"""The PIE check and the full run compare their external inputs with external-inputs.json first.

A PHAR or a JSONTestSuite checkout other than the pinned one would spend a whole build and run on
a record that the documentation check then rejects.
"""
from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_pie
import verification as test_runner
from verification_record import sha256, supplementary_manifest


def suite(folder):
    """A JSONTestSuite stand-in: a Git checkout with one parsing case."""
    root = Path(folder) / 'suite'
    (root / 'test_parsing').mkdir(parents=True)
    (root / 'test_parsing/y_fixture.json').write_text('[]')
    for command in (['init', '--quiet'], ['add', '.'],
                    ['-c', 'user.name=test', '-c', 'user.email=test@example.com', 'commit', '--quiet', '-m', 'suite']):
        subprocess.run(['git', *command], cwd=root, check=True, capture_output=True)
    return root


class ExternalPins(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ordered-json-pins-')
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.phar = self.folder / 'pie.phar'
        self.phar.write_text('<?php echo "not the pinned PIE";\n')

    def run_main(self, main, argv):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', argv), \
                redirect_stdout(output), redirect_stderr(errors):
            status = main()
        return status, output.getvalue() + errors.getvalue()

    def test_a_phar_other_than_the_pin_is_refused_before_pie_runs(self):
        with patch('check_pie.run_streamed') as pie:
            status, text = self.run_main(check_pie.main, ['check_pie.py', '--pie', str(self.phar)])
        self.assertEqual(status, 1, text)
        self.assertFalse(pie.called)
        self.assertIn(f'actual {sha256(self.phar.read_bytes())}', text)
        self.assertIn('expected b88792235c8e80be568436d4cb043b49fd1869c89b64e83d23e2882ae19d70a8', text)

    def test_a_suite_other_than_the_pin_is_refused_before_pie_runs(self):
        checkout = suite(self.folder)
        pin = {'pie': {'release': 'fixture', 'phar_sha256': sha256(self.phar.read_bytes())},
               'supplementary': {'project': 'nst/JSONTestSuite', 'revision': '1' * 40, 'cases': 1,
                                 'inputs_sha256': '2' * 64}}
        actual = supplementary_manifest(checkout)
        with patch('check_pie.external_inputs', return_value=pin), patch('check_pie.run_streamed') as pie:
            status, text = self.run_main(check_pie.main, ['check_pie.py', '--pie', str(self.phar),
                                                          '--suite', str(checkout)])
        self.assertEqual(status, 1, text)
        self.assertFalse(pie.called)
        self.assertIn(f"revision: expected {'1' * 40}, actual {actual['revision']}", text)
        self.assertIn(f"inputs_sha256: expected {'2' * 64}, actual {actual['inputs_sha256']}", text)

    def test_the_full_run_refuses_a_suite_other_than_the_pin_before_the_unit_tests(self):
        checkout = suite(self.folder)
        with patch('verification.run_unit_tests') as unit:
            status, text = self.run_main(test_runner.main, ['verification.py', '--suite', str(checkout)])
        self.assertEqual(status, 1, text)
        self.assertFalse(unit.called)
        self.assertIn('revision: expected 1ef36fa01286573e846ac449e8683f8833c5b26a, actual', text)


if __name__ == '__main__':
    unittest.main()

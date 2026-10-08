"""make check runs the lints that AGENTS requires, cargo clippy with -D warnings and go vet, as targets of their own."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lint

ROOT = Path(__file__).resolve().parents[2]


class Lints(unittest.TestCase):
    def test_the_lints_are_the_commands_of_agents(self):
        self.assertEqual(lint.LINTS, {
            'clippy': ('packages/ordered-json-rust', ['cargo', 'clippy', '--locked', '--all-targets', '--', '-D', 'warnings']),
            'go-vet': ('packages/ordered-json-go', ['go', 'vet', './...'])})
        agents = (ROOT / 'AGENTS.md').read_text()
        self.assertIn('cargo clippy --all-targets -- -D warnings', agents)
        self.assertIn('go vet ./...', agents)

    def run_lint(self, name, status):
        calls = []

        def run(label, command, cwd, env=None):
            calls.append((label, command, Path(cwd).relative_to(ROOT).as_posix(), env['CARGO_TARGET_DIR']))
            return subprocess.CompletedProcess(command, status, stdout='')

        with patch('lint.run_streamed', side_effect=run), \
                redirect_stdout(io.StringIO()) as printed:
            result = lint.main([name])
        return result, calls, printed.getvalue()

    def test_each_lint_runs_in_its_package_with_a_target_directory_of_its_run(self):
        for name, (folder, command) in lint.LINTS.items():
            with self.subTest(lint=name):
                result, calls, _ = self.run_lint(name, 0)
                self.assertEqual(result, 0)
                self.assertEqual([call[:3] for call in calls], [(name, command, folder)])
                target = Path(calls[0][3])
                self.assertFalse(target.exists(), 'the target directory of the run is removed')
                self.assertNotIn(str(ROOT), str(target))

    def test_a_lint_that_reports_fails_with_its_command(self):
        result, _, printed = self.run_lint('clippy', 101)
        self.assertEqual(result, 1)
        self.assertIn('clippy: cargo clippy --locked --all-targets -- -D warnings in packages/ordered-json-rust/ failed with exit 101', printed)

    def test_an_unknown_lint_fails_by_name(self):
        with redirect_stdout(io.StringIO()), patch('sys.stderr', io.StringIO()) as errors:
            self.assertEqual(lint.main(['fmt']), 2)
        self.assertIn('unknown lint fmt; the lints are clippy, go-vet', errors.getvalue())


if __name__ == '__main__':
    unittest.main()

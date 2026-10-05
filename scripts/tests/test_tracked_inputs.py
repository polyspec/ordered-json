"""Records, documentation checks and shared cases read the files Git tracks, never untracked files.

A file that is not committed is not part of the tree that a record names, so it must not change a
source manifest, a documentation result or the shared cases.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docs_check import authored_markdown, report_paths
from registry import fixture_paths
from verification_record import source_manifest


def git(root, *args):
    subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)


class TrackedInputs(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ordered-json-tracked-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        for name, text in {'scripts/tool.py': 'print(1)\n', 'README.md': '# Fixture\n',
                           'docs/report.json': '{}\n', 'fixtures/valid/object.json': '{}'}.items():
            self.write(name, text)
        git(self.root, 'init', '--quiet')
        git(self.root, 'add', '.')
        git(self.root, '-c', 'user.name=test', '-c', 'user.email=test@example.com', 'commit', '--quiet', '-m', 'fixture')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_an_untracked_file_does_not_change_the_source_manifest(self):
        before = source_manifest(self.root)
        self.write('scripts/untracked.py', 'print(2)\n')
        self.write('notes.txt', 'draft\n')
        self.assertEqual(source_manifest(self.root), before)
        self.assertEqual(sorted(before['files']), ['README.md', 'docs/report.json',
                                                    'fixtures/valid/object.json', 'scripts/tool.py'])

    def test_an_untracked_document_report_or_fixture_is_not_read(self):
        self.write('draft.md', '# Draft\n')
        self.write('docs/draft.json', '{"draft": true}\n')
        self.write('fixtures/valid/draft.json', '[]')
        self.assertEqual(authored_markdown(self.root), {'README.md'})
        self.assertEqual([path.relative_to(self.root).as_posix() for path in report_paths(self.root)],
                         ['docs/report.json'])
        self.assertEqual([path.name for path in fixture_paths(self.root, 'valid')], ['object.json'])

    def test_a_tree_without_git_reads_its_files(self):
        # A source archive has no Git metadata; every file in it is a source.
        plain = self.root / 'archive'
        (plain / 'fixtures/valid').mkdir(parents=True)
        (plain / 'fixtures/valid/a.json').write_text('1')
        (plain / 'readme.md').write_text('# A\n')
        subprocess.run(['rm', '-rf', str(self.root / '.git')], check=True)
        self.assertEqual([path.name for path in fixture_paths(plain, 'valid')], ['a.json'])
        self.assertEqual(authored_markdown(plain), {'readme.md'})


if __name__ == '__main__':
    unittest.main()

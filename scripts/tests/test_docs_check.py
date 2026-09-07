"""Exercise documentation failures with isolated, explicitly synthetic records."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docs_check import check_repository
from verification_record import IMPLEMENTATIONS, create_record, sha256, source_manifest, write_record
from test import build_extension


class DocumentationChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='ordered-json-docs-test-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write('js/index.js', 'export const fixture = true;\n')
        self.json('examples/official.json', {'cases': [{'id': 'fixture'}]})
        self.write('fixtures/valid/object.json', '{}')
        self.manifest = {'schema_version': 1, 'documents': [
            {'id': 'overview', 'kind': 'overview', 'en': 'README.md', 'ko': 'README.ko.md'},
            {'id': 'features', 'kind': 'state', 'en': 'docs/features.md', 'ko': 'docs/features.ko.md'},
        ]}
        self.json('docs/documentation-manifest.json', self.manifest)
        self.pair('README.md', 'overview',
            '# Fixture\n\n<a id="contract"></a>\n## Contract\n\n[Features](docs/features.md)\n'
            '\n~~~js\nconst text = "[code only](missing.json)";\n~~~\n')
        self.pair('docs/features.md', 'features',
            '# Features\n\n<a id="state"></a>\n## State\n\n'
            '| ID | Feature | Implementation | Verification | Evidence | Distribution | Specification |\n'
            '| --- | --- | --- | --- | --- | --- | --- |\n'
            '| F-ORDER | Order | implemented | shared-suite | [result](verification.json) | source-only | [contract](../README.md#contract) |\n')
        self.distribution = {'schema_version': 1, 'checked_at': '2026-09-07T00:00:00+00:00',
            'source': {'state': 'available', 'url': 'https://github.com/polyspec/ordered-json',
                       'branch': 'main', 'visibility': 'public'},
            'github_releases': [], 'version_tags': [],
            'registries': {name: {'state': 'not-verified'} for name in
                          ('npm', 'crates.io', 'packagist', 'go', 'php-extension')}}
        self.json('docs/distribution.json', self.distribution)
        self.results = {name: {'status': 'passed', 'cases': 2} for name in IMPLEMENTATIONS}
        self.versions = {name: {'version': 'synthetic fixture'} for name in IMPLEMENTATIONS}
        self.versions['php-extension'] = {'php': 'synthetic fixture', 'extension': 'ordered_json',
                                       'extension_version': 'synthetic fixture'}
        self.record = create_record(self.root, source_manifest(self.root), self.results,
                                   {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions)
        self.json('docs/verification.json', self.record)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def json(self, path, data):
        self.write(path, json.dumps(data, indent=2) + '\n')

    def pair(self, path, identifier, body):
        english = f'<!-- doc-id: {identifier} -->\n' + body
        self.write(path, english)
        self.write(path[:-3] + '.ko.md', f'<!-- source-sha256: {sha256(english.encode())} -->\n' + english)

    def change(self, path, old, new):
        original = (self.root / path).read_text()
        self.assertIn(old, original)
        self.write(path, original.replace(old, new))

    def assert_failure(self, text):
        errors, _, _ = check_repository(self.root)
        self.assertTrue(any(text in error for error in errors), errors)

    def test_valid_documents_ignore_links_inside_code(self):
        self.assertEqual(check_repository(self.root), ([], 2, 1))

    def test_missing_translation_fails(self):
        (self.root / 'README.ko.md').unlink()
        self.assert_failure('Missing link target: README.ko.md')

    def test_english_change_requires_translation_review(self):
        self.change('README.md', '# Fixture', '# Changed fixture')
        self.assert_failure('Translation revision differs')

    def test_missing_file_link_fails(self):
        self.change('README.md', 'docs/features.md', 'docs/missing.md')
        self.assert_failure('Missing link target: docs/missing.md')

    def test_missing_anchor_fails(self):
        self.change('docs/features.md', '#contract', '#missing')
        self.assert_failure('Missing explicit anchor')

    def test_reference_link_missing_target_fails(self):
        self.write('README.md', (self.root / 'README.md').read_text() + '\n[details][target]\n\n[target]: missing.md\n')
        self.assert_failure('Missing link target: missing.md')

    def test_undefined_reference_fails(self):
        self.write('README.md', (self.root / 'README.md').read_text() + '\n[details][undefined]\n')
        self.assert_failure('Undefined reference link')

    def test_unregistered_markdown_fails(self):
        self.write('docs/extra.md', '# Extra\n')
        self.assert_failure('Markdown document is not registered')

    def test_duplicate_topic_fails(self):
        self.manifest['documents'].append(self.manifest['documents'][0])
        self.json('docs/documentation-manifest.json', self.manifest)
        self.assert_failure('duplicate document ID')

    def test_mismatched_code_fails(self):
        self.change('README.ko.md', 'const text', 'let text')
        self.assert_failure('Fenced code blocks differ')

    def test_mismatched_sections_fail(self):
        self.change('README.ko.md', 'id="contract"', 'id="changed"')
        self.assert_failure('Section identifiers differ')

    def test_unclosed_fence_fails(self):
        self.write('README.md', (self.root / 'README.md').read_text() + '\n```sh\n')
        self.assert_failure('Unclosed fenced code block')

    def test_missing_feature_field_fails(self):
        self.change('docs/features.md', ' | source-only |', ' |')
        self.assert_failure('Feature rows require')

    def test_invalid_feature_state_fails(self):
        self.change('docs/features.md', '| implemented |', '| complete |')
        self.assert_failure('Invalid implementation state')

    def test_planned_feature_cannot_claim_passed_tests(self):
        self.change('docs/features.md', '| implemented |', '| planned |')
        self.assert_failure('Incomplete features cannot claim')

    def test_translated_status_must_match(self):
        self.change('docs/features.ko.md', '| source-only |', '| not-distributed |')
        self.assert_failure('English and Korean feature states')

    def test_verified_feature_requires_evidence(self):
        self.change('docs/features.md', '[result](verification.json)', 'none')
        self.assert_failure('requires verification.json evidence')

    def test_source_change_invalidates_old_result(self):
        self.write('js/index.js', 'export const fixture = false;\n')
        self.assert_failure('Verification is stale')

    def test_source_addition_invalidates_old_result(self):
        self.write('js/new.js', 'export const added = true;\n')
        self.assert_failure('Verification is stale')

    def test_source_deletion_invalidates_old_result(self):
        (self.root / 'js/index.js').unlink()
        self.assert_failure('Verification is stale')

    def test_missing_implementation_result_fails(self):
        del self.record['implementations']['php-extension']
        self.json('docs/verification.json', self.record)
        self.assert_failure('requires all registered implementations')

    def test_php_extension_and_runtime_versions_are_separate(self):
        del self.record['implementations']['php-extension']['runtime']['extension_version']
        self.json('docs/verification.json', self.record)
        self.assert_failure('PHP runtime and extension versions')

    def test_private_paths_in_markdown_fail(self):
        self.write('README.md', (self.root / 'README.md').read_text() + '\n/Users/example/project/\n')
        self.assert_failure('Public document contains a local home-directory path')

    def test_private_paths_in_reports_fail(self):
        self.json('docs/report.json', {'path': '/home/example/project/'})
        self.assert_failure('Public report contains a local home-directory path')

    def test_link_cannot_escape_repository(self):
        self.change('README.md', 'docs/features.md', '../../outside.md')
        self.assert_failure('Link escapes repository')

    def test_symlink_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'outside').symlink_to(outside, target_is_directory=True)
            self.change('README.md', 'docs/features.md', 'outside')
            self.assert_failure('Link escapes repository')

    def test_unobserved_publication_fails(self):
        for path in ('docs/features.md', 'docs/features.ko.md'):
            self.change(path, '| source-only |', '| published |')
        self.assert_failure('Published feature has no observed artifact')

    def test_partial_results_cannot_create_record(self):
        results = copy.deepcopy(self.results)
        del results['go']
        with self.assertRaisesRegex(ValueError, 'all registered implementations'):
            create_record(self.root, source_manifest(self.root), results,
                          {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions)

    def test_changed_sources_cannot_create_record(self):
        before = source_manifest(self.root)
        self.write('js/index.js', '// changed during run\n')
        with self.assertRaisesRegex(ValueError, 'Sources changed during verification'):
            create_record(self.root, before, self.results,
                          {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions)

    def test_failed_case_cannot_create_record(self):
        results = copy.deepcopy(self.results)
        results['js']['status'] = 'failed'
        with self.assertRaisesRegex(ValueError, 'must pass every case'):
            create_record(self.root, source_manifest(self.root), results,
                          {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions)

    def test_record_write_replaces_complete_json(self):
        target = self.root / 'docs/verification.json'
        write_record(target, self.record)
        self.assertEqual(json.loads(target.read_text()), self.record)
        self.assertEqual(list(target.parent.glob('.verification-*')), [])

    def test_native_build_rejects_copy_error_with_zero_exit_status(self):
        from subprocess import CompletedProcess
        result = CompletedProcess(['phpize'], 0, stdout='cp: generated-file: Permission denied\n')
        with patch('registry.subprocess.run', return_value=result), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'Build reported an error'):
                build_extension()


if __name__ == '__main__':
    unittest.main()

"""Exercise the failures of the evidence check with isolated, explicitly synthetic records."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_evidence import check_evidence, feature_rows
from registry import REGISTRY
from verification_record import (AGGREGATE_RECORD, IMPLEMENTATIONS, PIE_RECORD, create_record, sha256, source_manifest,
                                 write_record)
from verification import build_extension


class FeatureStateChecks(unittest.TestCase):
    def test_package_tests_require_verification_record(self):
        row = ('| ID | Feature | Implementation | Verification | Evidence | Distribution | Specification |\n'
               '| --- | --- | --- | --- | --- | --- | --- |\n'
               '| F-RUST-SERDE | Typed Rust values | implemented | package-tests | '
               '[result](operations/validation.md#records) | source-only | [contract](../README.md#contract) |')
        self.assertIn('F-RUST-SERDE', feature_rows(row))
        with self.assertRaisesRegex(ValueError, 'record that backs it'):
            feature_rows(row.replace('operations/validation.md#records', 'other.json'))


class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='ordered-json-docs-test-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write('js/index.js', 'export const fixture = true;\n')
        self.json('examples/official.json', {'cases': [{'id': 'fixture'}]})
        self.write('fixtures/valid/object.json', '{}')
        self.pair('docs/features.md', 'features',
            '# Features\n\n<a id="state"></a>\n## State\n\n'
            '| ID | Feature | Implementation | Verification | Evidence | Distribution | Specification |\n'
            '| --- | --- | --- | --- | --- | --- | --- |\n'
            '| F-ORDER | Order | implemented | shared-suite | [result](operations/validation.md#records) | source-only | [contract](../README.md#contract) |\n')
        self.distribution = {'schema_version': 1, 'checked_at': '2026-09-07T00:00:00+00:00',
            'source': {'state': 'available', 'url': 'https://github.com/polyspec/ordered-json',
                       'branch': 'main', 'visibility': 'public'},
            'github_releases': [], 'version_tags': [],
            'registries': {name: {'state': 'not-verified'} for name in
                          ('npm', 'crates.io', 'packagist', 'go', 'php-extension', 'pypi')}}
        self.json('docs/distribution.json', self.distribution)
        self.supplementary = {'project': 'nst/JSONTestSuite', 'revision': 'a' * 40,
                              'cases': 1, 'inputs_sha256': sha256(b'supplementary inputs')}
        self.json('external-inputs.json', {'schema_version': 1,
                  'pie': {'release': 'synthetic', 'url': 'https://example.invalid/pie',
                          'phar_sha256': sha256(b'pie tool')},
                  'supplementary': {**self.supplementary, 'url': 'https://example.invalid/suite'}})
        self.results = {name: {'status': 'passed', 'cases': 2} for name in IMPLEMENTATIONS}
        self.versions = {name: {'version': 'synthetic fixture'} for name in IMPLEMENTATIONS}
        self.versions['php-extension'] = {'php': 'synthetic fixture', 'extension': 'ordered_json',
                                       'extension_version': 'synthetic fixture'}
        self.package_tests = {name: {'status': 'passed', 'command': ['synthetic']}
                              for name in IMPLEMENTATIONS
                              if REGISTRY['implementations'][name].get('tests')}
        self.record = create_record(self.root, source_manifest(self.root), self.results,
                                   {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions,
                                   package_tests=self.package_tests)
        self.json(AGGREGATE_RECORD, self.record)

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
        errors, _ = check_evidence(self.root)
        self.assertTrue(any(text in error for error in errors), errors)

    def test_a_valid_record_passes(self):
        self.assertEqual(check_evidence(self.root), ([], 1))

    def test_missing_feature_field_fails(self):
        self.change('docs/features.md', ' | source-only |', ' |')
        self.assert_failure('Feature rows require')

    def test_invalid_feature_state_fails(self):
        self.change('docs/features.md', '| implemented |', '| complete |')
        self.assert_failure('Invalid implementation state')

    def features_with(self, before_table='', after=''):
        self.pair('docs/features.md', 'features',
            '# Features\n\n<a id="state"></a>\n## State\n\n' + before_table +
            '| ID | Feature | Implementation | Verification | Evidence | Distribution | Specification |\n'
            '| --- | --- | --- | --- | --- | --- | --- |\n'
            '| F-ORDER | Order | implemented | shared-suite | [result](operations/validation.md#records) | source-only | [contract](../README.md#contract) |\n'
            + after)

    def test_state_word_outside_implementation_cell_fails(self):
        self.features_with(after='\n<a id="limits"></a>\n## Limits\n\n`partial` marks work in progress.\n'
                                 '\n| Kind | State |\n| --- | --- |\n| work | planned |\n')
        errors, _ = check_evidence(self.root)
        # The Korean file starts with its source-sha256 line, so its lines are one further.
        for name, offset in (('docs/features.md', 0), ('docs/features.ko.md', 1)):
            self.assertIn(f'{name}:{14 + offset}:1: state `partial` stands outside the Implementation cell of a feature row', errors)
            self.assertIn(f'{name}:{18 + offset}:10: state `planned` stands outside the Implementation cell of a feature row', errors)
        self.assertEqual(len(errors), 4, errors)

    def test_paragraph_in_tracker_section_fails(self):
        self.features_with(before_table='`implemented` means the behavior exists.\n\n')
        errors, _ = check_evidence(self.root)
        for name, offset in (('docs/features.md', 0), ('docs/features.ko.md', 1)):
            self.assertIn(f'{name}:{7 + offset}:1: the line is not a row of the feature table; the section of the feature table holds only the table', errors)
            self.assertIn(f'{name}:{7 + offset}:1: state `implemented` stands outside the Implementation cell of a feature row', errors)
        self.assertEqual(len(errors), 4, errors)

    def test_planned_feature_cannot_claim_passed_tests(self):
        self.change('docs/features.md', '| implemented |', '| planned |')
        self.assert_failure('Incomplete features cannot claim')

    def test_translated_status_must_match(self):
        self.change('docs/features.ko.md', '| source-only |', '| not-distributed |')
        self.assert_failure('English and Korean feature states')

    def test_verified_feature_requires_evidence(self):
        self.change('docs/features.md', '[result](operations/validation.md#records)', 'none')
        self.assert_failure('names the record that backs it')

    def test_source_change_invalidates_old_result(self):
        self.write('js/index.js', 'export const fixture = false;\n')
        self.assert_failure('Verification is stale')

    def test_documentation_check_leaves_record_freshness_to_make_check(self):
        # A source edit must not force the full suite before a documentation review;
        # make check runs the checker with --records and still rejects a stale record.
        self.write('js/index.js', 'export const fixture = false;\n')
        script = str(Path(__file__).resolve().parents[1] / 'check_evidence.py')
        alone = subprocess.run([sys.executable, script, '--root', str(self.root)],
                               capture_output=True, text=True)
        self.assertEqual(alone.returncode, 0, alone.stderr)
        from verification import EVIDENCE_CHECK
        self.assertEqual(EVIDENCE_CHECK[1:], [script, '--records'])
        recorded = subprocess.run(EVIDENCE_CHECK + ['--root', str(self.root)], capture_output=True, text=True)
        self.assertEqual(recorded.returncode, 1)
        self.assertIn('Verification is stale', recorded.stderr)

    def test_records_are_the_output_of_the_run_not_committed_files(self):
        # A committed record goes stale with every commit, so it is not evidence: the checker reads the records
        # that the run wrote into var/records, and a file left in docs/ is not read.
        self.assertEqual((AGGREGATE_RECORD, PIE_RECORD),
                         ('var/records/verification.json', 'var/records/pie-verification.json'))
        stale = copy.deepcopy(self.record)
        stale['sources'] = {'sha256': '0' * 64, 'files': {}}
        self.json('docs/verification.json', stale)
        self.json('docs/pie-verification.json', {'schema_version': 1, 'scope': 'pie-build', 'status': 'passed'})
        errors, _ = check_evidence(self.root)
        self.assertEqual(errors, [])
        (self.root / AGGREGATE_RECORD).unlink()
        self.assert_failure('var/records/verification.json')

    def test_a_feature_names_the_record_section_of_the_validation_procedure(self):
        self.change('docs/features.md', '[result](operations/validation.md#records)', '[result](verification.json)')
        self.write('docs/verification.json', '{}')
        self.assert_failure('names the record that backs it')

    def test_source_addition_invalidates_old_result(self):
        self.write('js/new.js', 'export const added = true;\n')
        self.assert_failure('Verification is stale')

    def test_source_deletion_invalidates_old_result(self):
        (self.root / 'js/index.js').unlink()
        self.assert_failure('Verification is stale')

    def test_missing_implementation_result_fails(self):
        del self.record['implementations']['php-extension']
        self.json(AGGREGATE_RECORD, self.record)
        self.assert_failure('requires all registered implementations')

    def test_php_extension_and_runtime_versions_are_separate(self):
        del self.record['implementations']['php-extension']['runtime']['extension_version']
        self.json(AGGREGATE_RECORD, self.record)
        self.assert_failure('PHP runtime and extension versions')

    def test_private_paths_in_reports_fail(self):
        self.json('docs/report.json', {'path': '/' + 'home/example/project/'})
        self.assert_failure('Public report contains a local home-directory path')

    def test_source_observation_must_name_the_declared_repository(self):
        self.distribution['source'] = {'state': 'available', 'url': 'https://github.com/example/other',
                                       'branch': 'main', 'visibility': 'public'}
        self.json('docs/distribution.json', self.distribution)
        self.assert_failure('names the declared repository')

    def test_unobserved_publication_fails(self):
        for path in ('docs/features.md', 'docs/features.ko.md'):
            self.change(path, '| source-only |', '| published |')
        self.assert_failure('Published feature has no observed artifact')

    def test_partial_results_cannot_create_record(self):
        results = copy.deepcopy(self.results)
        del results['go']
        with self.assertRaisesRegex(ValueError, 'all registered implementations'):
            create_record(self.root, source_manifest(self.root), results,
                          {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions,
                          package_tests=self.package_tests)

    def test_changed_sources_cannot_create_record(self):
        before = source_manifest(self.root)
        self.write('js/index.js', '// changed during run\n')
        with self.assertRaisesRegex(ValueError, 'Sources changed during verification'):
            create_record(self.root, before, self.results,
                          {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions,
                          package_tests=self.package_tests)

    def test_failed_case_cannot_create_record(self):
        results = copy.deepcopy(self.results)
        results['js']['status'] = 'failed'
        with self.assertRaisesRegex(ValueError, 'must pass every case'):
            create_record(self.root, source_manifest(self.root), results,
                          {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions,
                          package_tests=self.package_tests)

    def test_missing_package_tests_cannot_create_record(self):
        with self.assertRaisesRegex(ValueError, 'Declared package tests must run and pass'):
            create_record(self.root, source_manifest(self.root), self.results,
                          {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions)

    def test_record_write_replaces_complete_json(self):
        target = self.root / AGGREGATE_RECORD
        write_record(target, self.record)
        self.assertEqual(json.loads(target.read_text()), self.record)
        self.assertEqual(list(target.parent.glob('.verification-*')), [])

    def supplementary_records(self):
        """An aggregate and a PIE record that use every kind of recorded hash."""
        supplementary = self.supplementary
        results = {name: {'status': 'passed', 'cases': 3} for name in IMPLEMENTATIONS}
        aggregate = create_record(self.root, source_manifest(self.root), results,
                                  {'official': 1, 'fixtures': 1, 'supplementary': 1}, 1, self.versions,
                                  supplementary, package_tests=self.package_tests)
        pie = {'schema_version': 1, 'scope': 'pie-build', 'status': 'passed',
               'checked_at': aggregate['checked_at'], 'platform': aggregate['platform'],
               'sources': aggregate['sources'], 'packages': aggregate['packages'],
               'pie': {'version': 'synthetic fixture', 'phar_sha256': sha256(b'pie tool')},
               'package': 'polyspec/ordered-json-extension:*@dev',
               'commands': [{'arguments': ['build'], 'exit_code': 0}], 'build_warnings': [],
               'artifact': {'path': 'php-extension/src/modules/ordered_json.so'},
               'cases': aggregate['cases'],
               'implementations': {'php-extension': {'status': 'passed', 'cases': 3,
                                                     'runtime': self.versions['php-extension']}},
               'supplementary': supplementary}
        return aggregate, pie

    def recorded_hashes(self, record, path=()):
        """Every recorded content hash or revision, by its path inside the record."""
        if isinstance(record, dict):
            for key, value in record.items():
                yield from self.recorded_hashes(value, path + (key,))
        elif isinstance(record, list):
            for index, value in enumerate(record):
                yield from self.recorded_hashes(value, path + (index,))
        elif isinstance(record, str) and re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}', record):
            yield path

    def assert_recorded_hashes_are_falsifiable(self, name, record, other):
        located = list(self.recorded_hashes(record))
        self.assertTrue(located, name)
        self.json(name, record)
        self.json(other[0], other[1])
        # Without this the mutations below could pass on an unrelated error.
        self.assertEqual(check_evidence(self.root)[0], [], 'The unchanged records must pass')
        for path in located:
            with self.subTest(field='.'.join(str(step) for step in path)):
                mutated = copy.deepcopy(record)
                target = mutated
                for step in path[:-1]:
                    target = target[step]
                value = target[path[-1]]
                target[path[-1]] = ('1' if value[0] == '0' else '0') + value[1:]
                self.json(name, mutated)
                self.json(other[0], other[1])
                errors, _ = check_evidence(self.root)
                self.assertTrue(errors, 'A changed hash must fail the check: ' + '.'.join(
                    str(step) for step in path))

    def test_every_recorded_aggregate_hash_is_falsifiable(self):
        aggregate, pie = self.supplementary_records()
        self.assert_recorded_hashes_are_falsifiable(
            AGGREGATE_RECORD, aggregate, (PIE_RECORD, pie))

    def test_every_recorded_pie_hash_is_falsifiable(self):
        aggregate, pie = self.supplementary_records()
        self.assert_recorded_hashes_are_falsifiable(
            PIE_RECORD, pie, (AGGREGATE_RECORD, aggregate))

    def features_body(self, evidence='[result](../benchmarks/results.json)'):
        return ('# Features\n\n<a id="state"></a>\n## State\n\n'
                '| ID | Feature | Implementation | Verification | Evidence | Distribution | Specification |\n'
                '| --- | --- | --- | --- | --- | --- | --- |\n'
                '| F-ORDER | Order | implemented | shared-suite | [result](operations/validation.md#records) | source-only | [contract](../README.md#contract) |\n'
                f'| F-BENCH | Speed | implemented | benchmark | {evidence} | source-only | [contract](../README.md#contract) |\n')

    def benchmark_repository(self):
        """A committed repository whose benchmark record was measured from a clean checkout."""
        workload = {'schema_version': 2,
                    'benchmark': {'warmup': 1, 'iterations': 1, 'samples': 1,
                                  'median_tolerance': 0.1, 'p95_tolerance': 0.3},
                    'fixtures': [{'file': 'empty-array.json', 'input_bytes': 3}]}
        self.json('benchmarks/workload.json', workload)
        self.pair('docs/features.md', 'features', self.features_body())
        self.json('benchmarks/results.json', {})
        # As in the repository, Git ignores var/, where the run writes its records.
        self.write('.gitignore', '/var/\n')
        for command in (['init', '--quiet'], ['add', '-A'],
                        ['-c', 'user.email=fixture@example.invalid', '-c', 'user.name=fixture',
                         'commit', '--quiet', '-m', 'fixture']):
            subprocess.run(['git', *command], cwd=self.root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        record = {'schema_version': 2, 'source': {'dirty': False},
                  'protocol': dict(workload['benchmark']), 'environment': {'system': 'synthetic'},
                  'fixtures': workload['fixtures'], 'results': [],
                  'comparison': {'status': 'baseline-updated'}}
        self.json('benchmarks/results.json', record)
        self.json(AGGREGATE_RECORD, create_record(
            self.root, source_manifest(self.root), self.results,
            {'official': 1, 'fixtures': 1, 'supplementary': 0}, 1, self.versions,
            package_tests=self.package_tests))
        # Without this the failures below could pass on an unrelated error.
        self.assertEqual(check_evidence(self.root)[0], [], 'The benchmark fixture must pass')
        return record

    def test_benchmark_evidence_must_name_the_benchmark_record(self):
        self.benchmark_repository()
        self.pair('docs/features.md', 'features', self.features_body('[result](operations/validation.md#records)'))
        self.assert_failure('names the record that backs it')

    def test_benchmark_measured_from_a_dirty_tree_is_not_evidence(self):
        record = self.benchmark_repository()
        record['source']['dirty'] = True
        self.json('benchmarks/results.json', record)
        self.assert_failure('measured from a clean checkout')

    def test_benchmark_source_names_only_whether_the_checkout_was_clean(self):
        record = self.benchmark_repository()
        record['source']['revision'] = 'main'
        self.json('benchmarks/results.json', record)
        self.assert_failure('The source of a benchmark result holds only `dirty`')

    def test_benchmark_protocol_must_match_the_workload(self):
        record = self.benchmark_repository()
        record['protocol']['samples'] = 2
        self.json('benchmarks/results.json', record)
        self.assert_failure('protocol the workload declares')

    def test_benchmark_fixtures_must_match_the_workload(self):
        record = self.benchmark_repository()
        record['fixtures'] = [{'file': 'other.json', 'input_bytes': 3}]
        self.json('benchmarks/results.json', record)
        self.assert_failure('inputs the workload declares')

    def test_failed_benchmark_comparison_is_not_evidence(self):
        record = self.benchmark_repository()
        record['comparison'] = {'status': 'failed'}
        self.json('benchmarks/results.json', record)
        self.assert_failure('failed benchmark comparison')

    def test_unreproducible_artifact_hash_cannot_be_recorded(self):
        aggregate, pie = self.supplementary_records()
        pie['artifact']['sha256'] = sha256(b'built artifact')
        self.json(AGGREGATE_RECORD, aggregate)
        self.json(PIE_RECORD, pie)
        self.assert_failure('carries its path alone')

    def test_recorded_artifact_must_be_the_declared_one(self):
        aggregate, pie = self.supplementary_records()
        pie['artifact'] = {'path': 'php-extension/src/modules/other.so'}
        self.json(AGGREGATE_RECORD, aggregate)
        self.json(PIE_RECORD, pie)
        self.assert_failure('artifact the registry declares')

    def test_native_build_rejects_copy_error_with_zero_exit_status(self):
        from subprocess import CompletedProcess
        result = CompletedProcess(['phpize'], 0, stdout='cp: generated-file: Permission denied\n')
        with patch('registry.run_streamed', return_value=result), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'Build reported an error'):
                build_extension()


if __name__ == '__main__':
    unittest.main()

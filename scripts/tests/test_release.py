"""The release of a tag (scripts/release.py, .github/workflows/release.yml).

Each case builds a Git repository in a temporary directory with the manifests of the release, a changelog, a branch
origin/main and the tag, and puts fakes of gh and npm first on PATH. The fake gh answers the check runs of the GitHub
API from a JSON state file and records each call; the fake npm writes a tarball that carries package.json as npm pack
does. No case of a sandbox reaches GitHub or a registry. InstallFromAssets builds the archives of the repository with the
real npm and git, and installs them with `npm ci` and `composer install` from the committed consumer fixtures of
scripts/tests/install in a temporary directory outside the repository.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import unittest
import unittest.mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install_fixtures
import release
from test import timeout

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = 'polyspec/ordered-json'

FAKE_GH = r'''
import json, os, sys
state_path = os.environ['FAKE_STATE']
state = json.load(open(state_path))
args = sys.argv[1:]
state['calls'].append(args)
if args[:2] == ['api', '--paginate']:
    for run in state['check_runs']:
        print(json.dumps([run['id'], run['name'], run['status'], run['conclusion']]))
elif args[:2] == ['release', 'create']:
    notes = args[args.index('--notes-file') + 1]
    state['notes'] = open(notes).read()
else:
    sys.exit(f'fake gh: unexpected arguments {args}')
json.dump(state, open(state_path, 'w'))
'''
FAKE_NPM = r'''
import json, os, sys, tarfile
args = sys.argv[1:]
assert args[0] == 'pack', args
manifest = json.load(open('package.json'))
name = manifest['name'].lstrip('@').replace('/', '-')
with tarfile.open(os.path.join(args[args.index('--pack-destination') + 1], f"{name}-{manifest['version']}.tgz"),
                  'w:gz') as packed:
    packed.add('package.json', 'package/package.json')
'''
CHANGELOG = '''# Changelog

<a id="unreleased"></a>
## Unreleased

- A change after the release.

<a id="0-0-1"></a>
## 0.0.1

- The first entry of 0.0.1.
- The second entry of 0.0.1.
'''


def git(root, *args):
    return subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@example.com', *args], cwd=root,
                          check=True, capture_output=True, text=True).stdout.strip()


class Sandbox:
    """A repository with the manifests of release.MANIFESTS at one version, a changelog, origin/main and fakes."""

    def __init__(self, test, version='0.0.1', changelog=CHANGELOG):
        folder = tempfile.TemporaryDirectory(prefix='ordered-json-release-')
        test.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / 'repository'
        self.bin = Path(folder.name) / 'bin'
        self.state = Path(folder.name) / 'state.json'
        self.root.mkdir()
        self.bin.mkdir()
        for name, source in (('gh', FAKE_GH), ('npm', FAKE_NPM)):
            (self.bin / name).write_text(f'#!{sys.executable}\n{source}')
            (self.bin / name).chmod(0o755)
        names = {path: name for _, path, name in release.PACKAGES}
        for manifest in release.MANIFESTS:
            path = self.root / manifest
            path.parent.mkdir(parents=True, exist_ok=True)
            package = names.get(str(Path(manifest).parent), '@polyspec/ordered-json')
            if path.name == 'package.json':
                path.write_text(json.dumps({'name': package, 'version': version}))
            elif path.name == 'composer.json':
                path.write_text(json.dumps({'name': package.lstrip('@'), 'version': version}))
            elif path.name == 'pyproject.toml':
                path.write_text(f'[project]\nname = "polyspec-ordered-json"\nversion = "{version}"\n')
            else:
                path.write_text(f'[package]\nname = "polyspec-ordered-json"\nversion = "{version}"\n\n[dependencies]\n')
        (self.root / 'php/src').mkdir()
        (self.root / 'php/src/OrderedJson.php').write_text('<?php\n')
        for directory, module in release.GO_MODULES.items():
            (self.root / directory).mkdir(exist_ok=True)
            (self.root / directory / 'go.mod').write_text(f'module {module}\n\ngo 1.22\n')
        (self.root / 'CHANGELOG.md').write_text(changelog)
        git(self.root, 'init', '--quiet', '--initial-branch=main')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '--quiet', '-m', 'release')
        self.commit = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'update-ref', 'refs/remotes/origin/main', self.commit)
        self.check_runs([('push-gate', 'success'), ('ci-passed', 'success')])
        patch = unittest.mock.patch.dict(os.environ, {'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}',
                                                      'FAKE_STATE': str(self.state)})
        patch.start()
        test.addCleanup(patch.stop)

    def check_runs(self, runs):
        self.state.write_text(json.dumps({'calls': [], 'check_runs': [
            {'id': index, 'name': name, 'status': 'completed' if conclusion else 'in_progress', 'conclusion': conclusion}
            for index, (name, conclusion) in enumerate(runs, 1)]}))

    def tag(self, tag, commit=None):
        git(self.root, 'tag', '-a', tag, '-m', tag, commit or self.commit)
        return tag

    def recorded(self):
        return json.loads(self.state.read_text())


class Tags(unittest.TestCase):
    def test_a_release_tag_is_a_version_or_a_go_module_directory_and_a_version(self):
        self.assertEqual(release.parse_tag('v0.0.1'), (None, '0.0.1'))
        self.assertEqual(release.parse_tag('v10.20.30'), (None, '10.20.30'))
        self.assertEqual(release.parse_tag('go/v0.0.1'), ('go', '0.0.1'))
        for tag in ('v1.0', '1.0.0', 'v01.0.0', 'v1.0.0-rc.1', 'vX.Y.Z', 'go/1.0.0'):
            with self.subTest(tag=tag), self.assertRaisesRegex(release.Stop, 'a release tag is vX.Y.Z'):
                release.parse_tag(tag)
        with self.assertRaisesRegex(release.Stop, r"other/v1.0.0: other is not a Go module directory; the Go modules "
                                                  r"are \['go'\]"):
            release.parse_tag('other/v1.0.0')


class Versions(unittest.TestCase):
    def test_every_manifest_at_the_version_and_the_changelog_section_pass(self):
        sandbox = Sandbox(self)
        self.assertEqual(release.versions(sandbox.root, 'v0.0.1'), '0.0.1')

    def test_a_version_mismatch_names_the_file_and_both_values(self):
        sandbox = Sandbox(self)
        cargo = sandbox.root / 'rust/Cargo.toml'
        cargo.write_text(cargo.read_text().replace('version = "0.0.1"', 'version = "0.0.2"'))
        package = sandbox.root / 'js/package.json'
        package.write_text(package.read_text().replace('"0.0.1"', '"0.1.0"'))
        with self.assertRaises(release.Stop) as stopped:
            release.versions(sandbox.root, 'v0.0.1')
        self.assertEqual(str(stopped.exception), 'js/package.json: version 0.1.0, the tag v0.0.1 is 0.0.1; '
                                                 'rust/Cargo.toml: version 0.0.2, the tag v0.0.1 is 0.0.1')

    def test_a_composer_manifest_without_a_version_fails_and_one_with_a_version_is_compared(self):
        sandbox = Sandbox(self)
        composer = sandbox.root / 'php/composer.json'
        composer.write_text(json.dumps({'name': 'polyspec/ordered-json'}))
        with self.assertRaisesRegex(release.Stop, r'^php/composer.json: no version, the tag v0.0.1 is 0.0.1$'):
            release.versions(sandbox.root, 'v0.0.1')
        composer.write_text(json.dumps({'name': 'polyspec/ordered-json', 'version': '0.0.2'}))
        with self.assertRaisesRegex(release.Stop, r'^php/composer.json: version 0.0.2, the tag v0.0.1 is 0.0.1$'):
            release.versions(sandbox.root, 'v0.0.1')

    def test_a_missing_changelog_section_fails(self):
        sandbox = Sandbox(self, version='0.0.2')
        with self.assertRaisesRegex(release.Stop, r'^CHANGELOG.md: no section ## 0.0.2 for the tag v0.0.2$'):
            release.versions(sandbox.root, 'v0.0.2')
        empty = Sandbox(self, changelog='# Changelog\n\n## Unreleased\n\n## 0.0.1\n\n<a id="x"></a>\n## 0.0.0\n')
        with self.assertRaisesRegex(release.Stop, r'^CHANGELOG.md: the section ## 0.0.1 has no entry for the tag v0.0.1$'):
            release.versions(empty.root, 'v0.0.1')

    def test_a_go_tag_requires_the_module_path_of_its_directory_and_the_changelog_section(self):
        sandbox = Sandbox(self, version='9.9.9')
        self.assertEqual(release.versions(sandbox.root, 'go/v0.0.1'), '0.0.1')
        (sandbox.root / 'go/go.mod').write_text('module github.com/polyspec/ordered-json\n')
        with self.assertRaisesRegex(release.Stop, r'^go/go.mod: module github.com/polyspec/ordered-json, the tag '
                                                  r'go/v0.0.1 is github.com/polyspec/ordered-json/go$'):
            release.versions(sandbox.root, 'go/v0.0.1')

    def test_the_section_is_the_release_notes_without_the_anchor_of_the_next_section(self):
        sandbox = Sandbox(self)
        self.assertEqual(release.changelog_section(sandbox.root, '0.0.1'),
                         '- The first entry of 0.0.1.\n- The second entry of 0.0.1.\n')
        self.assertEqual(release.changelog_section(sandbox.root, 'Unreleased'), '- A change after the release.\n')


class Verify(unittest.TestCase):
    def test_a_commit_of_main_with_both_checks_passed_is_verified(self):
        sandbox = Sandbox(self)
        commit, checks = release.verify(sandbox.root, sandbox.tag('v0.0.1'), REPOSITORY)
        self.assertEqual((commit, checks), (sandbox.commit, ['push-gate', 'ci-passed']))
        self.assertEqual(sandbox.recorded()['calls'], [
            ['api', '--paginate', f'repos/{REPOSITORY}/commits/{sandbox.commit}/check-runs?per_page=100',
             '--jq', '.check_runs[] | [.id, .name, .status, .conclusion] | @json']])

    def test_a_commit_that_is_not_on_main_fails(self):
        sandbox = Sandbox(self)
        git(sandbox.root, 'commit', '--quiet', '--allow-empty', '-m', 'outside main')
        outside = git(sandbox.root, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(release.Stop, f'^v0.0.1: the commit {outside} is not on origin/main; '):
            release.verify(sandbox.root, sandbox.tag('v0.0.1', outside), REPOSITORY)
        self.assertEqual(sandbox.recorded()['calls'], [])

    def test_a_missing_or_failed_check_is_named(self):
        cases = {
            'missing': ([('push-gate', 'success')], 'the check ci-passed is missing'),
            'failed': ([('push-gate', 'failure'), ('ci-passed', 'success')],
                       'the check push-gate is completed with the conclusion failure, not success'),
            'running': ([('push-gate', 'success'), ('ci-passed', None)],
                        'the check ci-passed is in_progress with the conclusion None, not success'),
            'both': ([], 'the check push-gate is missing; the check ci-passed is missing'),
        }
        for case, (runs, message) in cases.items():
            with self.subTest(case=case):
                sandbox = Sandbox(self)
                sandbox.check_runs(runs)
                with self.assertRaises(release.Stop) as stopped:
                    release.verify(sandbox.root, sandbox.tag('v0.0.1'), REPOSITORY)
                self.assertEqual(str(stopped.exception), f'v0.0.1: the commit {sandbox.commit}: {message}')

    def test_the_latest_run_of_a_check_decides(self):
        sandbox = Sandbox(self)
        sandbox.check_runs([('push-gate', 'success'), ('ci-passed', 'failure'), ('ci-passed', 'success')])
        self.assertEqual(release.verify(sandbox.root, sandbox.tag('v0.0.1'), REPOSITORY)[0], sandbox.commit)
        sandbox.check_runs([('push-gate', 'success'), ('ci-passed', 'success'), ('ci-passed', 'failure')])
        with self.assertRaisesRegex(release.Stop, 'the check ci-passed is completed with the conclusion failure'):
            release.verify(sandbox.root, 'v0.0.1', REPOSITORY)

    def test_without_the_repository_the_step_fails_before_any_request(self):
        sandbox = Sandbox(self)
        with self.assertRaisesRegex(release.Stop, 'GITHUB_REPOSITORY is not set'):
            release.verify(sandbox.root, sandbox.tag('v0.0.1'), None)


class Assets(unittest.TestCase):
    def test_an_asset_is_named_after_its_package_and_version(self):
        self.assertEqual(release.asset_name('@polyspec/ordered-json', '0.0.1', 'tgz'), 'polyspec-ordered-json-0.0.1.tgz')
        self.assertEqual(release.asset_name('polyspec/ordered-json-extension', '1.2.3', 'zip'),
                         'polyspec-ordered-json-extension-1.2.3.zip')
        self.assertEqual(release.asset_names('v0.0.1'), [
            'polyspec-ordered-json-0.0.1.tgz', 'polyspec-ordered-json-0.0.1.zip',
            'polyspec-ordered-json-extension-0.0.1.zip'])
        self.assertEqual(release.asset_names('go/v0.0.1'), [])

    def test_assets_builds_one_archive_per_package(self):
        sandbox = Sandbox(self)
        names = release.assets(sandbox.root, sandbox.tag('v0.0.1'))
        built = sorted(path.name for path in (sandbox.root / release.ASSETS).iterdir())
        self.assertEqual(built, sorted(names))
        self.assertEqual(sorted(names), sorted(release.asset_names('v0.0.1')))
        with zipfile.ZipFile(sandbox.root / release.ASSETS / 'polyspec-ordered-json-0.0.1.zip') as archive:
            self.assertEqual(sorted(archive.namelist()), ['composer.json', 'src/', 'src/OrderedJson.php'])

    def test_each_archive_carries_the_manifest_of_its_package_unchanged(self):
        sandbox = Sandbox(self)
        release.assets(sandbox.root, sandbox.tag('v0.0.1'))
        for kind, path, _ in release.PACKAGES:
            manifest = f"{path}/{'package.json' if kind == 'npm' else 'composer.json'}"
            archive = sandbox.root / release.ASSETS / release.asset_name(
                dict((name, package) for _, name, package in release.PACKAGES)[path], '0.0.1',
                'tgz' if kind == 'npm' else 'zip')
            with self.subTest(manifest=manifest):
                self.assertEqual(release.packed_manifest(archive), (sandbox.root / manifest).read_text())

    def test_a_packed_manifest_that_differs_from_its_source_fails(self):
        sandbox = Sandbox(self)
        tag = sandbox.tag('v0.0.1')
        package = sandbox.root / 'js/package.json'
        package.write_text(json.dumps({'name': '@polyspec/ordered-json', 'version': '0.0.1', 'private': False}))
        with self.assertRaisesRegex(release.Stop, r'^polyspec-ordered-json-0.0.1.tgz: its manifest differs from '
                                                  r'js/package.json of the commit [0-9a-f]{40}; the archive carries '
                                                  r'the manifest unchanged$'):
            release.assets(sandbox.root, tag)

    def test_a_manifest_outside_the_standard_form_fails_before_any_archive(self):
        sandbox = Sandbox(self)
        (sandbox.root / 'php/composer.json').write_text(json.dumps({
            'name': 'polyspec/ordered-json', 'version': '0.0.1',
            'repositories': [{'type': 'path', 'url': '../php-extension'}],
            'require': {'polyspec/ordered-json-extension': '@dev'}}))
        git(sandbox.root, 'commit', '--quiet', '-am', 'repositories')
        sandbox.commit = git(sandbox.root, 'rev-parse', 'HEAD')
        with self.assertRaises(release.Stop) as stopped:
            release.assets(sandbox.root, sandbox.tag('v0.0.1'))
        self.assertEqual(str(stopped.exception),
                         "php/composer.json: declares repositories; a published composer.json resolves only by name "
                         "and version; php/composer.json: require polyspec/ordered-json-extension is '@dev', a "
                         "constraint with @dev")
        self.assertEqual(list((sandbox.root / release.ASSETS).iterdir()), [])

    def test_the_standard_form_names_every_departure(self):
        texts = {
            'php/composer.json': json.dumps({'name': 'polyspec/a', 'require': {
                'polyspec/b': '^0.0.1', 'vendor/c': 'dev-main@dev', 'php': '>=8.2'}}),
            'js/package.json': json.dumps({'name': '@polyspec/a', 'version': '0.0.1', 'overrides': {}, 'dependencies': {
                '@polyspec/b': '~0.0.1', '@polyspec/c': 'file:../c', 'd': 'git+https://example.com/d.git',
                '@polyspec/e': 'workspace:*', 'f': '^1.0.0'}, 'peerDependencies': {'@polyspec/g': '0.0.1'}}),
        }
        self.assertEqual(release.manifest_issues(texts), [
            'php/composer.json: no version X.Y.Z; a Composer artifact repository reads the version of the manifest, so '
            'a published composer.json declares it',
            "php/composer.json: require polyspec/b is '^0.0.1', not one exact version X.Y.Z",
            "php/composer.json: require vendor/c is 'dev-main@dev', a constraint with @dev",
            'js/package.json: declares overrides; a published package.json resolves only by name and version',
            "js/package.json: dependencies @polyspec/b is '~0.0.1', not one exact version X.Y.Z",
            "js/package.json: dependencies @polyspec/c is 'file:../c', not a registry version",
            "js/package.json: dependencies d is 'git+https://example.com/d.git', not a registry version",
            "js/package.json: dependencies @polyspec/e is 'workspace:*', not a registry version",
        ])

    def test_a_go_tag_builds_no_archive(self):
        sandbox = Sandbox(self)
        self.assertEqual(release.assets(sandbox.root, sandbox.tag('go/v0.0.1')), [])
        self.assertEqual(list((sandbox.root / release.ASSETS).iterdir()), [])


class InstallFromAssets(unittest.TestCase):
    """The archives of the repository install as a consumer installs them, from the committed fixtures of
    scripts/tests/install (make install-fixtures), in a temporary directory outside the repository.

    The fixtures are a package.json with its package-lock.json, which depends on the tarball by its release name, and a
    composer.json with its composer.lock, which requires the library from an artifact repository of the zips with
    Packagist disabled. The archives are built in this run, so the locks record them by name and version only. `npm ci` runs with an empty cache and the scope
    @polyspec pointed at an unreachable registry, so a polyspec package can come only from its tarball, and `composer
    install` with an empty COMPOSER_HOME and COMPOSER_CACHE_DIR. Neither runs offline: a third-party package of a lock
    is downloaded at its locked version and hash. Composer reads the extension zip but does not install a package of
    the type php-ext, which PIE installs, so the fixture requires the library, and the extension zip is listed from the
    artifact repository."""

    @classmethod
    def setUpClass(cls):
        folder = tempfile.TemporaryDirectory(prefix='ordered-json-install-')
        cls.addClassCleanup(folder.cleanup)
        cls.folder = Path(folder.name)
        cls.version = install_fixtures.version()
        # The working tree as a commit, without changing the checkout: git stash create prints nothing for a clean tree.
        commit = git(ROOT, 'stash', 'create') or git(ROOT, 'rev-parse', 'HEAD')
        assets = cls.folder / 'assets'
        assets.mkdir()
        release.build_assets(ROOT, commit, cls.version, assets)
        install_fixtures.stage(cls.folder / 'work', assets)
        cls.work = cls.folder / 'work'

    def run_in(self, command, cwd, env):
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f'{" ".join(command)}:\n{result.stdout}\n{result.stderr}\n'
                                               f'make install-fixtures writes the fixtures of the working tree')
        return result.stdout

    def test_the_locks_record_the_archives_by_name_and_version_only(self):
        npm = json.loads((install_fixtures.FIXTURES / 'npm/package-lock.json').read_text())
        entry = npm['packages']['node_modules/@polyspec/ordered-json']
        self.assertEqual((entry['version'], entry['resolved']),
                         (self.version, 'file:' + release.asset_name('@polyspec/ordered-json', self.version, 'tgz')))
        self.assertNotIn('integrity', entry)
        composer = json.loads((install_fixtures.FIXTURES / 'composer/composer.lock').read_text())
        self.assertEqual([(entry['name'], entry['version'], entry['dist']['shasum']) for entry in composer['packages']],
                         [('polyspec/ordered-json', self.version, '')])

    def test_the_fixtures_are_those_of_the_version(self):
        for path, text in install_fixtures.manifests(self.version).items():
            with self.subTest(fixture=path):
                self.assertEqual((install_fixtures.FIXTURES / path).read_text(), text,
                                 'make install-fixtures writes the fixtures of the version')

    @timeout(120)
    def test_npm_ci_installs_the_tarball_of_the_lock(self):
        project = self.work / 'npm'
        env = install_fixtures.npm_environment(True)
        self.run_in(['npm', 'ci', '--cache', str(self.folder / 'npm-cache'),
                     f'--@polyspec:registry={install_fixtures.UNREACHABLE}', '--no-audit', '--no-fund'], project, env)
        installed = json.loads((project / 'node_modules/@polyspec/ordered-json/package.json').read_text())
        self.assertEqual(installed['version'], self.version)
        output = self.run_in(['node', '--input-type=module', '-e',
                              "import {parse, stringify} from '@polyspec/ordered-json';"
                              "console.log(stringify(parse('{\"b\":1,\"a\":2}')));"], project, env)
        self.assertEqual(output.strip(), '{"b":1,"a":2}')

    @timeout(120)
    def test_composer_install_installs_the_zip_of_the_lock(self):
        project = self.work / 'composer'
        env = install_fixtures.composer_environment(self.folder, True)
        self.run_in(['composer', 'install', '--no-interaction', '--no-progress'], project, env)
        installed = json.loads((project / 'vendor/composer/installed.json').read_text())
        self.assertEqual([(entry['name'], entry['version']) for entry in installed['packages']],
                         [('polyspec/ordered-json', self.version)])
        listed = json.loads(self.run_in(['composer', 'show', '--available', '--format=json',
                                         'polyspec/ordered-json-extension'], project, env))
        self.assertEqual(listed['versions'], [self.version])
        self.assertEqual(listed['type'], 'php-ext')
        output = self.run_in(['php', '-r', "require 'vendor/autoload.php';"
                              "echo Polyspec\\OrderedJson\\stringify(Polyspec\\OrderedJson\\Value::parse('{\"b\":1,\"a\":2}'));"],
                             project, env)
        self.assertEqual(output, '{"b":1,"a":2}')


class Publish(unittest.TestCase):
    def test_publish_creates_the_release_with_the_notes_and_the_archives(self):
        sandbox = Sandbox(self)
        tag = sandbox.tag('v0.0.1')
        release.assets(sandbox.root, tag)
        self.assertEqual(release.publish(sandbox.root, tag), release.asset_names(tag))
        recorded = sandbox.recorded()
        call = recorded['calls'][-1]
        notes = call[call.index('--notes-file') + 1]
        self.assertEqual(call, ['release', 'create', 'v0.0.1', '--verify-tag', '--title', 'v0.0.1', '--notes-file', notes,
                                *[str(sandbox.root / release.ASSETS / name) for name in release.asset_names(tag)]])
        self.assertEqual(recorded['notes'], '- The first entry of 0.0.1.\n- The second entry of 0.0.1.\n')

    def test_a_go_tag_creates_a_release_without_archives(self):
        sandbox = Sandbox(self)
        tag = sandbox.tag('go/v0.0.1')
        self.assertEqual(release.publish(sandbox.root, tag), [])
        call = sandbox.recorded()['calls'][-1]
        self.assertEqual(call[:7], ['release', 'create', 'go/v0.0.1', '--verify-tag', '--title', 'go/v0.0.1', '--notes-file'])
        self.assertEqual(len(call), 8)

    def test_a_section_over_the_limit_is_one_line_that_links_the_section_of_the_tag(self):
        entry = '- ' + 'x' * (release.NOTES_LIMIT - 2) + '\n'
        changelog = CHANGELOG.replace('- The second entry of 0.0.1.\n', '- The second entry of 0.0.1.\n' + entry)
        sandbox = Sandbox(self, changelog=changelog)
        release.publish(sandbox.root, sandbox.tag('go/v0.0.1'))
        self.assertEqual(sandbox.recorded()['notes'],
                         'The changes of 0.0.1 are listed in [CHANGELOG.md]'
                         '(https://github.com/polyspec/ordered-json/blob/go/v0.0.1/CHANGELOG.md#0-0-1).\n')

    def test_a_section_without_an_explicit_anchor_links_the_anchor_of_its_heading(self):
        entry = '- ' + 'x' * release.NOTES_LIMIT + '\n'
        changelog = CHANGELOG.replace('<a id="0-0-1"></a>\n', '') + entry
        sandbox = Sandbox(self, changelog=changelog)
        release.publish(sandbox.root, sandbox.tag('go/v0.0.1'))
        self.assertEqual(sandbox.recorded()['notes'],
                         'The changes of 0.0.1 are listed in [CHANGELOG.md]'
                         '(https://github.com/polyspec/ordered-json/blob/go/v0.0.1/CHANGELOG.md#001).\n')

    def test_a_section_of_exactly_the_limit_in_characters_is_kept_whole(self):
        entry = '- ' + '\uac00' * (release.NOTES_LIMIT - 3) + '\n'
        changelog = CHANGELOG.split('- The first entry of 0.0.1.')[0] + entry
        sandbox = Sandbox(self, changelog=changelog)
        release.publish(sandbox.root, sandbox.tag('go/v0.0.1'))
        notes = sandbox.recorded()['notes']
        self.assertEqual(notes, entry)
        self.assertEqual(len(notes), release.NOTES_LIMIT)

    def test_publish_without_the_archives_fails_before_any_request(self):
        sandbox = Sandbox(self)
        with self.assertRaisesRegex(release.Stop, r'var/release/assets lacks \[.*\]; make release-assets builds them'):
            release.publish(sandbox.root, sandbox.tag('v0.0.1'))
        self.assertEqual(sandbox.recorded()['calls'], [])


class Repository(unittest.TestCase):
    def test_the_declarations_cover_every_tracked_manifest(self):
        tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, check=True, capture_output=True, text=True).stdout.split()
        manifests = sorted(path for path in tracked if not path.startswith('scripts/tests/install/')
                           and Path(path).name in ('package.json', 'composer.json', 'Cargo.toml', 'VERSION', 'pyproject.toml'))
        self.assertEqual(manifests, sorted(release.MANIFESTS))
        modules = sorted(str(Path(path).parent) for path in tracked if Path(path).name == 'go.mod')
        self.assertEqual(modules, sorted(release.GO_MODULES))
        for kind, path, name in release.PACKAGES:
            manifest = {'npm': 'package.json', 'composer': 'composer.json'}[kind]
            self.assertEqual(json.loads((ROOT / path / manifest).read_text())['name'], name, path)

    def test_the_assets_are_npm_tarballs_and_composer_zips_and_a_crate_is_consumed_by_git_tag(self):
        self.assertEqual(sorted({kind for kind, _, _ in release.PACKAGES}), ['composer', 'npm'])
        archived = sorted(f"{path}/{'package.json' if kind == 'npm' else 'composer.json'}"
                          for kind, path, _ in release.PACKAGES)
        self.assertEqual(sorted(name for name, how in release.MANIFESTS.items() if how == release.ARCHIVE), archived)
        for name, how in release.MANIFESTS.items():
            with self.subTest(manifest=name):
                self.assertIn(how, (release.ARCHIVE, release.CHECKOUT, release.GIT_TAG))
                if Path(name).name in ('Cargo.toml', 'pyproject.toml'):
                    self.assertEqual(how, 'not released as an archive; consumed by git tag')
                if how == release.CHECKOUT:
                    self.assertEqual(Path(name).parent, Path('.'))
        source = (ROOT / 'scripts/release.py').read_text()
        self.assertNotIn("'cargo', 'package'", source)
        self.assertNotIn('.crate', source)

    def test_every_published_manifest_is_in_the_standard_form(self):
        self.assertEqual(release.manifest_issues(release.published_manifests(ROOT)), [])

    def test_the_released_versions_pass_the_version_check(self):
        # The version of the repository is the one of js/package.json, which every release sets; the check of its tag passes.
        version = json.loads((ROOT / 'js/package.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(release.versions(ROOT, f'v{version}'), version)
        self.assertEqual(release.versions(ROOT, 'go/v0.0.3'), '0.0.3')

    def test_make_runs_each_step_with_the_tag_of_the_environment(self):
        environment = {name: value for name, value in os.environ.items()
                       if name not in ('MAKEFLAGS', 'MFLAGS', 'MAKELEVEL', 'TAG', 'PYTHON')}
        for step in ('verify', 'versions', 'assets', 'publish'):
            with self.subTest(step=step):
                listed = subprocess.run(['make', '-n', f'release-{step}', 'PYTHON=python3'], cwd=ROOT,
                                        env={**environment, 'TAG': 'v0.0.1'}, capture_output=True, text=True)
                self.assertEqual(listed.returncode, 0, listed.stderr)
                self.assertEqual(listed.stdout.splitlines(), [f'python3 scripts/release.py {step} "$TAG"'])
                missing = subprocess.run(['make', f'release-{step}'], cwd=ROOT, env=environment, capture_output=True,
                                         text=True)
                self.assertNotEqual(missing.returncode, 0)
                self.assertIn(f'make release-{step} needs TAG=<tag>', missing.stderr)


if __name__ == '__main__':
    unittest.main()

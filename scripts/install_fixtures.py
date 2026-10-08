#!/usr/bin/env python3
"""Write the consumer fixtures of the release asset install test (scripts/tests/install, make install-fixtures).

    python3 scripts/install_fixtures.py

The fixtures are the manifests and locks of a consumer project that installs the release archives of the version of
js/package.json: npm/package.json depends on the tarball of @polyspec/ordered-json by its release name (`file:`), and
composer/composer.json requires polyspec/ordered-json at the version from an artifact repository `assets` of the
zips, with Packagist disabled. This script builds the archives of the working tree with release.build_assets, writes
both manifests, and writes package-lock.json with `npm install --package-lock-only` and composer.lock with `composer
update --no-install`, in a temporary directory with an empty npm cache, the scope @polyspec pointed at an unreachable
registry, and an empty COMPOSER_HOME and COMPOSER_CACHE_DIR, offline as every command other than make tools. The
archives of this repository are built in the run of the test, so the locks record them by name and version only: no
`integrity` in package-lock.json and an empty `shasum` in composer.lock. A third-party package keeps its version and
its integrity or shasum. A lock thus changes only when a release version or a dependency changes; the release commit
runs this script.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import release

ROOT = release.ROOT
FIXTURES = ROOT / 'scripts/tests/install'
UNREACHABLE = 'http://127.0.0.1:9/'
NPM_PROJECT = 'ordered-json-install-check'
COMPOSER_PROJECT = 'polyspec/ordered-json-install-check'


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def version():
    return json.loads((ROOT / 'js/package.json').read_text(encoding='utf-8'))['version']


def manifests(version):
    """{fixture path: text} of the consumer manifests of version."""
    tarball = release.asset_name('@polyspec/ordered-json', 'npm', version, 'tgz')
    npm = {'name': NPM_PROJECT, 'private': True, 'type': 'module',
           'dependencies': {'@polyspec/ordered-json': f'file:{tarball}'}}
    composer = {'name': COMPOSER_PROJECT, 'type': 'project',
                'repositories': [{'type': 'artifact', 'url': 'assets'}, {'packagist.org': False}],
                'require': {'polyspec/ordered-json': version}}
    return {'npm/package.json': json.dumps(npm, indent=2) + '\n',
            'composer/composer.json': json.dumps(composer, indent=2) + '\n'}


def npm_environment(online):
    """The environment of an npm run of a fixture with the pinned npm; online drops the offline setting, as an install
    of a consumer runs."""
    env = release.environment(ROOT)
    if online:
        env.pop('npm_config_offline', None)
    return env


def composer_environment(folder, online):
    """The environment of a Composer run of a fixture with an empty COMPOSER_HOME and COMPOSER_CACHE_DIR in folder;
    online drops the offline setting, as an install of a consumer runs."""
    env = {**release.environment(ROOT), 'COMPOSER_HOME': str(folder / 'composer-home'),
           'COMPOSER_CACHE_DIR': str(folder / 'composer-cache')}
    if online:
        env.pop('COMPOSER_DISABLE_NETWORK', None)
    return env


def unpin_own_archives(npm_lock, composer_lock):
    """Record the archives of this repository by name and version only: drop the `integrity` of every @polyspec entry
    of package-lock.json and empty the `shasum` of every polyspec dist of composer.lock."""
    data = json.loads(npm_lock.read_text(encoding='utf-8'))
    for path, entry in data.get('packages', {}).items():
        if path.startswith('node_modules/@polyspec/'):
            entry.pop('integrity', None)
    npm_lock.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    data = json.loads(composer_lock.read_text(encoding='utf-8'))
    for entry in data.get('packages', []) + data.get('packages-dev', []):
        if entry['name'].startswith('polyspec/') and 'dist' in entry:
            entry['dist']['shasum'] = ''
    composer_lock.write_text(json.dumps(data, indent=4) + '\n', encoding='utf-8')


def stage(folder, assets):
    """Copy the fixtures into folder/npm and folder/composer with the archives of assets: the tarball next to
    package.json and the zips in composer/assets."""
    for kind in ('npm', 'composer'):
        shutil.copytree(FIXTURES / kind, folder / kind)
    for archive in Path(assets).iterdir():
        if archive.suffix == '.tgz':
            shutil.copy2(archive, folder / 'npm' / archive.name)
        else:
            (folder / 'composer/assets').mkdir(exist_ok=True)
            shutil.copy2(archive, folder / 'composer/assets' / archive.name)


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        raise release.Stop(f'{" ".join(command)} exited with {result.returncode}: '
                           f'{result.stderr.strip() or result.stdout.strip()}')
    return result.stdout


def main():
    current = version()
    with tempfile.TemporaryDirectory(prefix='ordered-json-fixtures-') as name:
        folder = Path(name)
        assets = folder / 'assets'
        assets.mkdir()
        # The working tree as a commit, without changing the checkout: git stash create prints nothing for a clean tree.
        release.build_assets(ROOT, git('stash', 'create') or git('rev-parse', 'HEAD'), current, assets)
        for path, text in manifests(current).items():
            (FIXTURES / path).write_text(text, encoding='utf-8')
        for lock in ('npm/package-lock.json', 'composer/composer.lock'):
            (FIXTURES / lock).unlink(missing_ok=True)
        stage(folder / 'work', assets)
        work = folder / 'work'
        run(['npm', 'install', '--package-lock-only', '--cache', str(folder / 'npm-cache'),
             f'--@polyspec:registry={UNREACHABLE}', '--no-audit', '--no-fund'], work / 'npm', npm_environment(False))
        run(['composer', 'update', '--no-install', '--no-interaction', '--no-progress'], work / 'composer',
            composer_environment(folder, False))
        shutil.copy2(work / 'npm/package-lock.json', FIXTURES / 'npm/package-lock.json')
        shutil.copy2(work / 'composer/composer.lock', FIXTURES / 'composer/composer.lock')
        unpin_own_archives(FIXTURES / 'npm/package-lock.json', FIXTURES / 'composer/composer.lock')
    print(f'[install-fixtures] wrote the fixtures of {current} in {FIXTURES.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (release.Stop, OSError, subprocess.CalledProcessError) as error:
        print(f'[install-fixtures] failed: {error}', file=sys.stderr)
        sys.exit(1)

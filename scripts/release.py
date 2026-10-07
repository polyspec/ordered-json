#!/usr/bin/env python3
"""Release a tag of a commit of main: the steps of .github/workflows/release.yml.

    python3 scripts/release.py verify TAG     the tagged commit is on main and passed the checks push-gate and ci-passed
    python3 scripts/release.py versions TAG   every manifest of the tag has its version and CHANGELOG.md its section
    python3 scripts/release.py assets TAG     build the archive of every package of the tag into var/release/assets
    python3 scripts/release.py publish TAG    create the GitHub Release of the tag with its notes and archives

Every change reaches main through the merge queue with the required checks, so every commit of main passed the full
suite; the maintainer releases by tagging a commit of main after a version-bump pull request, and a tag push runs
these steps in order. A tag `vX.Y.Z` releases the packages of PACKAGES at version X.Y.Z; a tag `<directory>/vX.Y.Z`
releases the Go module of that directory (GO_MODULES), which needs no archive. No step reruns the tests.

`verify` resolves the tag to its commit, requires that commit to be an ancestor of origin/main (`git merge-base
--is-ancestor`) and reads the check runs of the commit from the GitHub API (`gh api
repos/<repository>/commits/<sha>/check-runs`, the repository of GITHUB_REPOSITORY): the latest run of each of
push-gate and ci-passed must be completed with the conclusion success. `versions` compares X.Y.Z with the version of
every manifest of MANIFESTS (a composer.json without a `version` field takes its version from the tag, as Composer
does) and requires the section `## X.Y.Z` in CHANGELOG.md; for a Go tag it requires the module path of the go.mod of
the directory. `assets` builds one archive per package, named `<package name>-<version>.<ext>` with `@scope/` written
as `scope-` and `vendor/` as `vendor-`: `npm pack` (.tgz) and a zip of the directory of a Composer package from `git
archive` of the tagged commit (.zip). The Cargo package is not released as an archive; it is consumed by git tag,
because `cargo package` rewrites git dependencies into crates.io requirements that do not resolve. A Go tag builds and
attaches nothing. `publish` runs `gh release create TAG --verify-tag --title TAG --notes-file <notes>`
with the archives of `assets`; the notes are the section X.Y.Z when it has at most NOTES_LIMIT (125000) characters,
the limit of GitHub, and otherwise the one line `The changes of X.Y.Z are listed in [CHANGELOG.md](<URL>).`, whose URL
is CHANGELOG.md at the tag with the anchor of the section. Each failure names the tag, the file or check and both values, and exits with status
1.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

from toolchains import environment

ROOT = Path(__file__).resolve().parents[1]
MAIN = 'origin/main'
CHECKS = ('push-gate', 'ci-passed')
CHANGELOG = 'CHANGELOG.md'
ASSETS = 'var/release/assets'
REPOSITORY = 'polyspec/ordered-json'
# GitHub refuses the body of a release over this many characters.
NOTES_LIMIT = 125000
# The packages that a tag vX.Y.Z releases as archives, one archive each: (kind, directory, package name). The release
# assets are npm tarballs and Composer zips only.
PACKAGES = (
    ('npm', 'js', '@polyspec/ordered-json'),
    ('composer', 'php', 'polyspec/ordered-json'),
    ('composer', 'php-extension', 'polyspec/ordered-json-extension'),
)
ARCHIVE = 'released as an archive'
CHECKOUT = 'installs the packages from a checkout of the repository'
GIT_TAG = 'not released as an archive; consumed by git tag'
# The manifests whose version a tag vX.Y.Z sets, each with how the tag releases it: the archive of its package, the
# manifests of the repository root, which install the same packages from a checkout, and the Cargo package, which is
# consumed by git tag because `cargo package` rewrites git dependencies into crates.io requirements that do not resolve.
MANIFESTS = {
    'package.json': CHECKOUT,
    'js/package.json': ARCHIVE,
    'composer.json': CHECKOUT,
    'php/composer.json': ARCHIVE,
    'php-extension/composer.json': ARCHIVE,
    'rust/Cargo.toml': GIT_TAG,
}
# The Go modules: a tag <directory>/vX.Y.Z releases the module of that directory.
GO_MODULES = {'go': 'github.com/polyspec/ordered-json/go'}
TAG = re.compile(r'(?:(?P<directory>[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*)/)?v(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))')


class Stop(Exception):
    """A step fails; the message names the cause."""


def parse_tag(tag):
    """(Go module directory or None, version) of a release tag."""
    found = TAG.fullmatch(tag)
    if not found:
        raise Stop(f'{tag}: a release tag is vX.Y.Z or <Go module directory>/vX.Y.Z')
    directory = found.group('directory')
    if directory is not None and directory not in GO_MODULES:
        raise Stop(f'{tag}: {directory} is not a Go module directory; the Go modules are {sorted(GO_MODULES)}')
    return directory, found.group('version')


def run(command, cwd, env=None):
    """The standard output of a command; Stop with the command, its exit status and its standard error."""
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    except OSError as error:
        raise Stop(f'{" ".join(command)} could not start: {error}')
    if result.returncode:
        raise Stop(f'{" ".join(command)} exited with {result.returncode}: '
                   f'{result.stderr.strip() or result.stdout.strip()}')
    return result.stdout


def tagged_commit(root, tag):
    return run(['git', 'rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}'], root).strip()


def verify(root, tag, repository):
    """The tagged commit is on main and the latest run of every check of CHECKS concluded success."""
    parse_tag(tag)
    if not repository:
        raise Stop('GITHUB_REPOSITORY is not set; it names the repository <owner>/<name> whose check runs are read')
    commit = tagged_commit(root, tag)
    ancestry = subprocess.run(['git', 'merge-base', '--is-ancestor', commit, MAIN], cwd=root, capture_output=True,
                              text=True)
    if ancestry.returncode == 1:
        raise Stop(f'{tag}: the commit {commit} is not on {MAIN}; a release tags a commit of main')
    if ancestry.returncode:
        raise Stop(f'git merge-base --is-ancestor {commit} {MAIN} exited with {ancestry.returncode}: '
                   f'{ancestry.stderr.strip()}')
    listed = run(['gh', 'api', '--paginate', f'repos/{repository}/commits/{commit}/check-runs?per_page=100',
                  '--jq', '.check_runs[] | [.id, .name, .status, .conclusion] | @json'], root)
    runs = [json.loads(line) for line in listed.splitlines() if line.strip()]
    problems = []
    for name in CHECKS:
        named = [entry for entry in runs if entry[1] == name]
        if not named:
            problems.append(f'the check {name} is missing')
            continue
        _, _, status, conclusion = max(named, key=lambda entry: entry[0])
        if status != 'completed' or conclusion != 'success':
            problems.append(f'the check {name} is {status} with the conclusion {conclusion}, not success')
    if problems:
        raise Stop(f'{tag}: the commit {commit}: ' + '; '.join(problems))
    return commit, [name for name in CHECKS]


def manifest_version(path):
    """The version that a manifest declares, or None for a composer.json without one."""
    text = path.read_text(encoding='utf-8')
    if path.name in ('package.json', 'composer.json'):
        data = json.loads(text)
        if path.name == 'composer.json' and 'version' not in data:
            return None
        return data.get('version')
    if path.name == 'Cargo.toml':
        section = re.search(r'(?ms)^\[package\]\s*$(.*?)(?=^\[|\Z)', text)
        found = section and re.search(r'(?m)^version\s*=\s*"([^"]*)"', section.group(1))
        return found.group(1) if found else None
    raise Stop(f'{path.name}: not a manifest of a release')


def changelog_section(root, version):
    """The body of the section `## version` of CHANGELOG.md, without the anchor of the next section."""
    path = Path(root) / CHANGELOG
    lines = path.read_text(encoding='utf-8').splitlines()
    if f'## {version}' not in lines:
        raise Stop(f'{CHANGELOG}: no section ## {version}')
    start = lines.index(f'## {version}') + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith('## ')), len(lines))
    body = lines[start:end]
    while body and (not body[-1].strip() or re.fullmatch(r'<a id="[^"]*"></a>', body[-1].strip())):
        body.pop()
    while body and not body[0].strip():
        body.pop(0)
    if not body:
        raise Stop(f'{CHANGELOG}: the section ## {version} has no entry')
    return '\n'.join(body) + '\n'


def changelog_anchor(root, version):
    """The anchor of the section `## version`: the id of the `<a id>` line above the heading, or the anchor that GitHub
    generates for the heading, the version without its dots."""
    lines = (Path(root) / CHANGELOG).read_text(encoding='utf-8').splitlines()
    above = [line.strip() for line in lines[:lines.index(f'## {version}')] if line.strip()]
    explicit = re.fullmatch(r'<a id="([^"]*)"></a>', above[-1]) if above else None
    return explicit.group(1) if explicit else version.replace('.', '')


def release_notes(root, tag):
    """The section of the version of the tag when it fits NOTES_LIMIT characters, otherwise one line that links the
    section in CHANGELOG.md at the tag."""
    _, version = parse_tag(tag)
    section = changelog_section(root, version)
    if len(section) <= NOTES_LIMIT:
        return section
    url = (f'https://github.com/{REPOSITORY}/blob/{quote(tag, safe="/")}/{CHANGELOG}'
           f'#{changelog_anchor(root, version)}')
    return f'The changes of {version} are listed in [{CHANGELOG}]({url}).\n'


def versions(root, tag):
    """Every manifest of the tag declares its version, and CHANGELOG.md has the section of the version."""
    root = Path(root)
    directory, version = parse_tag(tag)
    problems = []
    if directory is None:
        for name in MANIFESTS:
            declared = manifest_version(root / name)
            if declared is not None and declared != version:
                problems.append(f'{name}: version {declared}, the tag {tag} is {version}')
    else:
        found = re.search(r'(?m)^module\s+(\S+)\s*$', (root / directory / 'go.mod').read_text(encoding='utf-8'))
        module = found.group(1) if found else None
        if module != GO_MODULES[directory]:
            problems.append(f'{directory}/go.mod: module {module}, the tag {tag} is {GO_MODULES[directory]}')
    try:
        changelog_section(root, version)
    except Stop as error:
        problems.append(f'{error} for the tag {tag}')
    if problems:
        raise Stop('; '.join(problems))
    return version


def asset_name(name, version, extension):
    """<package name>-<version>.<ext>: `@scope/name` is written `scope-name` and `vendor/name` `vendor-name`."""
    return f"{name.lstrip('@').replace('/', '-')}-{version}.{extension}"


def asset_names(tag):
    directory, version = parse_tag(tag)
    if directory is not None:
        return []
    extensions = {'npm': 'tgz', 'composer': 'zip'}
    return [asset_name(name, version, extensions[kind]) for kind, _, name in PACKAGES]


def assets(root, tag):
    """Build the archive of every package of the tag into ASSETS; the names of the archives."""
    root = Path(root)
    directory, version = parse_tag(tag)
    target = root / ASSETS
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    if directory is not None:
        return []
    commit = tagged_commit(root, tag)
    env = environment(root)
    for (kind, path, name), expected in zip(PACKAGES, asset_names(tag)):
        if kind == 'npm':
            run(['npm', 'pack', '--pack-destination', str(target)], root / path, env)
        else:
            run(['git', 'archive', '--format=zip', f'--output={target / expected}', f'{commit}:{path}'], root)
    present = sorted(item.name for item in target.iterdir())
    if present != sorted(asset_names(tag)):
        raise Stop(f'{ASSETS} holds {present}, not the archives {sorted(asset_names(tag))}')
    return asset_names(tag)


def publish(root, tag):
    """Create the GitHub Release of the tag with release_notes as notes and the archives of assets."""
    root = Path(root)
    notes = release_notes(root, tag)
    names = asset_names(tag)
    target = root / ASSETS
    missing = [name for name in names if not (target / name).is_file()]
    if missing:
        raise Stop(f'{ASSETS} lacks {missing}; make release-assets builds them')
    with tempfile.TemporaryDirectory(prefix='release-notes-') as folder:
        notes_file = Path(folder) / 'notes.md'
        notes_file.write_text(notes, encoding='utf-8')
        run(['gh', 'release', 'create', tag, '--verify-tag', '--title', tag, '--notes-file', str(notes_file),
             *[str(target / name) for name in names]], root)
    return names


def main(argv, root=ROOT, environ=os.environ):
    if len(argv) != 2 or argv[0] not in ('verify', 'versions', 'assets', 'publish') or not argv[1]:
        print(__doc__, file=sys.stderr)
        return 2
    mode, tag = argv
    try:
        if mode == 'verify':
            commit, checks = verify(root, tag, environ.get('GITHUB_REPOSITORY'))
            print(f'[release] {tag}: the commit {commit} is on {MAIN} and passed {", ".join(checks)}')
        elif mode == 'versions':
            version = versions(root, tag)
            covered = ('every manifest of the tag declares' if parse_tag(tag)[0] is None
                       else f'{parse_tag(tag)[0]}/go.mod declares its module path, the version is')
            print(f'[release] {tag}: {covered} {version} and {CHANGELOG} has ## {version}')
        elif mode == 'assets':
            names = assets(root, tag)
            print(f'[release] {tag}: built {", ".join(names) if names else "no archive (a Go module)"} in {ASSETS}')
        else:
            names = publish(root, tag)
            print(f'[release] {tag}: created the GitHub Release with {", ".join(names) if names else "no archive"}')
    except (Stop, OSError, ValueError) as error:
        print(f'[release] {mode} {tag} failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

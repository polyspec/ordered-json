#!/usr/bin/env python3
"""Check the tool versions that the tracked pin files name, before any work.

    python3 scripts/toolchains.py           check every pin and print each mismatch
    python3 scripts/toolchains.py install   install the pinned Rust toolchain and npm (make tools)
    python3 scripts/toolchains.py pin TOOL  print the pinned version of TOOL (node, rust, go, python, npm)

Each pin is an exact release in a tracked file: Node.js in .node-version, Rust in rust-toolchain.toml,
Go in the toolchain line of go/go.mod, Python by major.minor in .python-version and npm in the packageManager field of
package.json. A run that uses other tools than the pins verifies the tree with tools that no record
names, so every entry point (scripts/test.py, scripts/verify.py, scripts/check_pie.py and
benchmarks/run.py) calls require() before its first step and fails with the expected and the actual
version of each tool that differs, or the error of the command that reports it.

No command installs or selects a tool on demand: GOTOOLCHAIN=local keeps go from downloading the
toolchain of go.mod, and RUSTUP_AUTO_INSTALL=0 keeps rustup from installing the toolchain of
rust-toolchain.toml on the first cargo. `make tools` installs the Rust toolchain and the pinned npm
once. packageManager names npm with the SHA-512 of its registry tarball, `npm@<version>+sha512.<hex>`;
the install downloads that tarball, refuses it unless the hash matches, unpacks it without links into
.cache/tools/npm of the checkout, which Git ignores, and publishes it by renaming a complete directory.
Its bin directory comes first on PATH, so no npm of the machine is used or changed; make itself runs
no tool by name, since GNU Make 3.81 looks a simple recipe command up on its own PATH, not the
exported one.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = {'GOTOOLCHAIN': 'local', 'RUSTUP_AUTO_INSTALL': '0'}
FIX = 'run make tools'


NPM_TARBALL = 'https://registry.npmjs.org/npm/-/npm-{version}.tgz'
LAUNCHER = '#!/bin/sh\nexec node "$(dirname "$0")/../package/bin/npm-cli.js" "$@"\n'


def npm_directory(root=ROOT):
    """The bin directory of the npm that make tools installs into the checkout."""
    return Path(root) / '.cache/tools/npm/bin'


def npm_pin(root=ROOT):
    """The pinned npm release and the SHA-512 of its tarball, from packageManager of package.json."""
    path = Path(root) / 'package.json'
    manager = json.loads(path.read_text(encoding='utf-8')).get('packageManager', '') if path.is_file() else ''
    match = re.fullmatch(r'npm@(\d+\.\d+\.\d+)\+sha512\.([0-9a-f]{128})', manager)
    if not match:
        raise ValueError('package.json packageManager does not pin an exact npm release with the SHA-512 of its '
                         'tarball (npm@<version>+sha512.<hex>)')
    return match[1], match[2]


def pins(root=ROOT):
    """Each tool with its pinned version and the tracked file that pins it. A missing or inexact pin
    raises ValueError naming the file."""
    root = Path(root)

    def read(name, pattern, label=None):
        path = root / name
        text = path.read_text(encoding='utf-8') if path.is_file() else ''
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            raise ValueError(f'{label or name} does not pin an exact version')
        return match[1], label or name

    npm = npm_pin(root)
    return {
        'node': read('.node-version', r'\A(\d+\.\d+\.\d+)\s*\Z'),
        'rust': read('rust-toolchain.toml', r'^channel\s*=\s*"(\d+\.\d+\.\d+)"\s*$'),
        'go': read('go/go.mod', r'^toolchain\s+(go\d+\.\d+\.\d+)\s*$', 'go/go.mod toolchain'),
        # Python is pinned by minor release: actions/python-versions builds no 3.9.6 for the CI image, so
        # no patch release is available both locally and on CI. The running patch release is recorded.
        'python': read('.python-version', r'\A(\d+\.\d+)\s*\Z'),
        'npm': (npm[0], 'package.json packageManager'),
    }


def environment(root=ROOT, base=None):
    """The environment of every command of a run: no toolchain download or install, and the npm of
    the checkout first on PATH."""
    base = dict(os.environ if base is None else base)
    return {**base, **ENVIRONMENT, 'PATH': str(npm_directory(root)) + os.pathsep + base.get('PATH', '')}


def run_version(command, cwd, env):
    """The standard output of a version command; CalledProcessError or OSError when it fails."""
    return subprocess.run(command, cwd=cwd, env=env, check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def failure(command, error):
    """The error of a version command, with the tool's own message."""
    if isinstance(error, subprocess.CalledProcessError):
        detail = (error.stderr or '').strip() or (error.stdout or '').strip()
        return f'{" ".join(command)} failed with exit {error.returncode}: {detail}'
    return f'{" ".join(command)} failed: {error}'


def problems(root=ROOT):
    """One message per tool that differs from its pin: the tool, the expected version with the file
    that pins it, and the actual version or the error of the command that reports it."""
    root = Path(root)
    try:
        expected = pins(root)
    except (ValueError, OSError) as error:
        return [f'pins: {error}']
    env = environment(root)
    found = []

    def compare(tool, command, cwd, parse):
        version, source = expected[tool]
        try:
            actual = parse(run_version(command, cwd, env))
        except (OSError, subprocess.CalledProcessError) as error:
            found.append(f'{tool}: expected {version} ({source}), actual: {failure(command, error)}')
            return
        if actual != version:
            found.append(f'{tool}: expected {version} ({source}), actual {actual}')

    compare('node', ['node', '--version'], root, lambda out: out.strip().removeprefix('v'))
    # rustup reads rust-toolchain.toml from the working directory and its parents.
    compare('rust', ['rustc', '--version'], root, lambda out: (out.split() + ['', ''])[1])
    compare('go', ['go', 'env', 'GOVERSION'], root / 'go', lambda out: out.strip())
    python, source = expected['python']
    if '.'.join(platform.python_version().split('.')[:2]) != python:
        found.append(f'python: expected {python} ({source}, major.minor), actual {platform.python_version()} '
                     f'({sys.executable})')
    npm, source = expected['npm']
    local = npm_directory(root) / 'npm'
    resolved = shutil.which('npm', path=env['PATH'])
    if resolved is None or Path(resolved).resolve() != local.resolve():
        found.append(f'npm: expected {npm} ({source}) from {local}, actual {resolved or "no npm on PATH"}; {FIX}')
    else:
        compare('npm', [str(local), '--version'], root, lambda out: out.strip())
    return found


def download(url):
    with urllib.request.urlopen(url, timeout=600) as response:
        return response.read()


def unpack(data, target):
    """Unpack a tarball into target: regular files and directories only, each under target."""
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive.getmembers():
            name = Path(member.name)
            if name.is_absolute() or '..' in name.parts:
                raise ValueError(f'the npm tarball names a path outside its directory: {member.name}')
            if not (member.isfile() or member.isdir()):
                raise ValueError(f'the npm tarball holds a link or a special file: {member.name}')
            destination = target / name
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.extractfile(member).read())
            destination.chmod(0o755 if member.mode & 0o111 else 0o644)


def install_npm(root=ROOT, fetch=download):
    """Install the pinned npm into .cache/tools/npm unless that exact tarball is installed there."""
    version, digest = npm_pin(root)
    tool = npm_directory(root).parent
    marker = tool / 'tarball.sha512'
    if marker.is_file() and marker.read_text().strip() == digest and (npm_directory(root) / 'npm').is_file():
        print(f'npm {version}: installed in {tool}')
        return
    url = NPM_TARBALL.format(version=version)
    data = fetch(url)
    actual = hashlib.sha512(data).hexdigest()
    if actual != digest:
        raise ValueError(f'npm {version} tarball {url}: expected sha512 {digest} (package.json packageManager), '
                         f'actual {actual}')
    tool.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='npm-', dir=tool.parent))
    retired = None
    try:
        unpack(data, staging)
        (staging / 'bin').mkdir()
        (staging / 'bin/npm').write_text(LAUNCHER)
        (staging / 'bin/npm').chmod(0o755)
        (staging / 'tarball.sha512').write_text(digest + '\n')
        if tool.exists():
            retired = Path(tempfile.mkdtemp(prefix='npm-retired-', dir=tool.parent))
            os.replace(tool, retired / 'npm')
        os.replace(staging, tool)
    finally:
        for leftover in (staging, retired):
            if leftover is not None and leftover.exists():
                shutil.rmtree(leftover)
    print(f'npm {version}: installed {url} into {tool}')


def install(root=ROOT):
    """make tools: the Rust toolchain of rust-toolchain.toml and the pinned npm, then the check."""
    subprocess.run(['rustup', 'toolchain', 'install', '--no-self-update'], cwd=root, check=True,
                   env=environment(root))
    install_npm(root)
    return require(root)


def require(root=ROOT):
    """Set the environment of the run and check every pin; print each mismatch and return False when
    a tool differs. Every entry point calls this before its first step."""
    os.environ.update(environment(root))
    found = problems(root)
    for problem in found:
        print(f'toolchain mismatch: {problem}', file=sys.stderr)
    if found:
        print(f'{len(found)} {"tool differs" if len(found) == 1 else "tools differ"} from the tracked pins; install the pinned '
              f'releases ({FIX} installs Rust and npm) and run again', file=sys.stderr)
    return not found


def main(argv):
    if argv == ['install']:
        return 0 if install() else 1
    if len(argv) == 2 and argv[0] == 'pin' and argv[1] in pins():
        print(pins()[argv[1]][0])
        return 0
    if argv:
        print(__doc__, file=sys.stderr)
        return 2
    if not require():
        return 1
    print('toolchains: ' + ', '.join(f'{tool} {version}' for tool, (version, _) in pins().items()))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

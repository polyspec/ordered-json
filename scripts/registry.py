"""Load implementation commands and resolve monorepo package paths."""
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
# The machine formats of a case listing (scripts/verify.py listed_cases): one case id per line, the
# terse list of the Rust test harness, and the JSON events of go test -json.
LISTING_FORMATS = ('lines', 'cargo-terse', 'go-test-json')


def load_registry(root=ROOT):
    registry = json.loads((root / 'implementations.json').read_text())
    if registry.get('schema_version') != 1:
        raise ValueError('Unsupported implementation registry schema')
    repositories, implementations = registry['repositories'], registry['implementations']
    if not repositories or not implementations:
        raise ValueError('The registry requires repositories and implementations')
    if not re.fullmatch(r'https://\S+\.git', registry.get('url', '')):
        raise ValueError('The registry declares one repository URL for every package')
    for name, repository in repositories.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
            raise ValueError('Invalid repository name: ' + name)
        path = Path(repository['path'])
        if path.is_absolute() or '..' in path.parts or str(path) == '.':
            raise ValueError('Repository paths must be relative child directories')
    for name, implementation in implementations.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
            raise ValueError('Invalid implementation name: ' + name)
        required = [implementation['repository']] + implementation.get('dependencies', [])
        if any(repository not in repositories for repository in required):
            raise ValueError('Implementation references an unknown repository: ' + name)
        commands = [implementation['command']] + list(implementation['runtime'].values())
        commands += [step['command'] for step in implementation.get('prepare', [])]
        for key in ('tests', 'test_cases', 'api_symbols'):
            declaration = implementation.get(key)
            if declaration is not None:
                # A case listing also names the machine format of its output.
                allowed = {'cwd', 'command', 'format'} if key == 'test_cases' else {'cwd', 'command'}
                if (not isinstance(declaration, dict) or not {'cwd', 'command'} <= set(declaration) <= allowed
                        or not declaration['cwd']):
                    raise ValueError(f'{key} declares cwd and command: ' + name)
                if key == 'test_cases' and declaration.get('format', 'lines') not in LISTING_FORMATS:
                    raise ValueError(f'test_cases format is one of {", ".join(LISTING_FORMATS)}: ' + name)
                commands.append(declaration['command'])
        if any(not command or not isinstance(command, list) or
               any(not isinstance(argument, str) for argument in command) for command in commands):
            raise ValueError('Commands must be nonempty argument lists: ' + name)
        if not isinstance(implementation.get('build_in_copy', False), bool):
            raise ValueError('build_in_copy is true or false: ' + name)
        environment = implementation.get('env', {})
        if not isinstance(environment, dict) or any(
                not isinstance(key, str) or not isinstance(value, str) for key, value in environment.items()):
            raise ValueError('env maps variable names to strings: ' + name)
        artifacts = implementation.get('artifacts')
        if artifacts is not None and (not isinstance(artifacts, list) or not artifacts or any(
                not isinstance(path, str) or not path for path in artifacts)):
            raise ValueError('Declared artifacts must be nonempty paths: ' + name)
    return registry


REGISTRY = load_registry()
IMPLEMENTATIONS = tuple(REGISTRY['implementations'])


def repository_paths(root=ROOT, overrides=None, registry=REGISTRY):
    result = {name: (root / entry['path']).resolve() for name, entry in registry['repositories'].items()}
    for name, path in (overrides or {}).items():
        if name not in result:
            raise ValueError('Unknown repository override: ' + name)
        result[name] = Path(path).resolve()
    return result


def required_repositories(selected, registry=REGISTRY):
    required = set()
    for name in selected:
        implementation = registry['implementations'][name]
        required.update([implementation['repository']] + implementation.get('dependencies', []))
    return sorted(required)


def tracked_files(root):
    """The paths, relative to root, of the files Git tracks under root, in name order; None when root
    is not in a Git work tree, as in a source archive, where every file is a source.

    An untracked file is not part of the tree that a record names, so no record, documentation check
    or shared case reads one."""
    process = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=root,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode:
        if 'not a git repository' in process.stderr:
            return None
        raise RuntimeError(f'git rev-parse --is-inside-work-tree in {root} exited with {process.returncode}: '
                           f'{process.stderr.strip()}')
    listing = subprocess.run(['git', 'ls-files', '--cached', '-z'], cwd=root,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return sorted(name for name in listing.stdout.decode('utf-8').split('\0') if name)


def files_under(root, directory, suffix, recursive):
    """The files with the suffix in directory, a path relative to root, and with recursive in its
    subdirectories: the tracked ones in a Git work tree, every one otherwise; in path order."""
    base = Path(root) / directory
    tracked = tracked_files(root)
    if tracked is None:
        found = base.rglob('*' + suffix) if recursive else base.glob('*' + suffix)
        return sorted(path for path in found if path.is_file())
    prefix = (Path(directory).as_posix().rstrip('/') + '/') if str(directory) not in ('', '.') else ''
    return [Path(root) / name for name in tracked
            if name.startswith(prefix) and name.endswith(suffix)
            and (recursive or '/' not in name[len(prefix):]) and (Path(root) / name).is_file()]


def fixture_paths(root, category):
    """The shared fixtures of one category, valid or invalid, in name order."""
    return files_under(root, 'fixtures/' + category, '.json', recursive=False)


@dataclass(frozen=True)
class Run:
    """One verification run: its temporary root, the repository paths its commands use, and
    the cache directory that receives built probes."""
    root: Path
    paths: dict
    cache: Path


def copy_sources(source, target):
    """Copy the files Git tracks under source, without untracked files or ignored build output; a tree
    without Git metadata is copied whole.

    A symbolic link is rejected, because the copy must hold the bytes the checkout holds."""
    names = tracked_files(source)
    if names is None:
        names = sorted(path.relative_to(source).as_posix() for path in Path(source).rglob('*')
                       if path.is_file() or path.is_symlink())
    count = 0
    for name in names:
        path = source / name
        if path.is_symlink():
            raise ValueError('A build source is a symbolic link: ' + str(path))
        if not path.is_file():
            continue  # A tracked file deleted in the checkout is not a source of this run.
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        count += 1
    print(f'copied {count} source files from {source} to {target}', flush=True)


@contextmanager
def run_directory(selected, paths, registry=REGISTRY):
    """Give one run its own temporary directory and remove it when the run ends.

    The cache for built probes lies in that directory. A repository whose implementation
    declares build_in_copy is copied there and its commands use the copy, so a build never
    cleans or replaces files in the checkout that another run uses."""
    with tempfile.TemporaryDirectory(prefix='ordered-json-run-') as folder:
        root = Path(folder).resolve()
        print(f'run directory: {root}', flush=True)
        run_paths = dict(paths)
        for name in selected:
            implementation = registry['implementations'][name]
            repository = implementation['repository']
            if implementation.get('build_in_copy') and run_paths[repository] == paths[repository]:
                copy = root / registry['repositories'][repository]['path']
                copy_sources(paths[repository], copy)
                run_paths[repository] = copy
        yield Run(root, run_paths, root / 'cache')


def context(paths, cache):
    cache.mkdir(parents=True, exist_ok=True)
    return {**{name: str(path) for name, path in paths.items()}, 'cache': str(cache),
            'cargo': shutil.which('cargo') or str(Path.home() / '.cargo/bin/cargo'),
            'rustc': shutil.which('rustc') or str(Path.home() / '.cargo/bin/rustc')}


def expand(value, variables):
    for name, replacement in variables.items():
        value = value.replace('{' + name + '}', replacement)
    if re.search(r'\{[a-z][a-z0-9-]*\}', value):
        raise ValueError('Unknown command variable: ' + value)
    return value


def command_environment(name, variables, registry=REGISTRY):
    """The environment of every command of an implementation: the caller's, with the variables the
    implementation declares under env, or None when it declares none. A declared variable replaces the
    caller's value, so a build output path such as CARGO_TARGET_DIR points into the run."""
    declared = registry['implementations'][name].get('env')
    if not declared:
        return None
    return dict(os.environ, **{key: expand(value, variables) for key, value in declared.items()})


def artifact_paths(name, paths, registry=REGISTRY):
    """The files a prepared build leaves behind, as the registry declares them."""
    variables = {key: str(value) for key, value in paths.items()}
    return [Path(expand(value, variables))
            for value in registry['implementations'][name].get('artifacts', [])]


# How often a reader that waits for output checks whether the process it reads has exited.
POLL_SECONDS = 0.2


def end_group(process):
    """Kill the process group of a process started with start_new_session, grandchildren included,
    and reap the process. A group whose processes have all ended is already gone; macOS reports EPERM
    for a group whose remaining members are killed processes that their new parent has not reaped."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    process.wait()


def next_chunk(process, stream, seconds=float('inf')):
    """The next output of stream within seconds: bytes, b'' at its end, or None when the seconds pass
    without output. The stream ends at end of file, or when the process has exited: its group is then
    killed, so a grandchild that keeps the stream open neither holds the reader nor survives the run."""
    deadline = time.monotonic() + seconds
    while True:
        wait = min(POLL_SECONDS, max(deadline - time.monotonic(), 0))
        if select.select([stream], [], [], wait)[0]:
            return os.read(stream.fileno(), 65536)
        if process.poll() is not None:
            end_group(process)
            # Every writer of the group is gone; what it wrote is read, then end of file.
            if select.select([stream], [], [], 1)[0]:
                return os.read(stream.fileno(), 65536)
            return b''
        if time.monotonic() >= deadline:
            return None


def run_streamed(label, command, cwd, env=None):
    """Run a build command, printing a start line, each output line as it arrives, and the
    exit status with the elapsed time. A build has no time limit: it ends with its own exit
    status, and the caller judges that status and the output. The process group, grandchildren
    included, is killed when the command ends or the caller is interrupted."""
    print(f'{label}: start', flush=True)
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    pending, lines = b'', []

    def emit(raw):
        text = raw.decode('utf-8', 'replace').rstrip('\r')
        lines.append(text)
        print(f'{label}: {text}', flush=True)

    try:
        while True:
            chunk = next_chunk(process, process.stdout)
            if not chunk:
                break
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                emit(line)
        if pending:
            emit(pending)
        returncode = process.wait()
    finally:
        end_group(process)
        process.stdout.close()
    print(f'{label}: exit {returncode} after {(time.monotonic() - started) * 1000:.0f} ms', flush=True)
    return subprocess.CompletedProcess(command, returncode, stdout=''.join(line + '\n' for line in lines))


class Failures(RuntimeError):
    """Every failure of a step that ran each language to its end. `failures` holds one message per
    failure and `languages` the implementations that failed."""

    def __init__(self, failures, languages=()):
        self.failures, self.languages = list(failures), set(languages)
        super().__init__('\n'.join(self.failures))


def prepare(selected, paths, cache, registry=REGISTRY):
    """Run the prepare steps of every selected implementation. A failed step ends the build of its
    implementation only; the others build to their end, and Failures then names every failure."""
    variables = context(paths, cache)
    warnings, failures, failed = [], [], set()
    for name in required_repositories(selected, registry):
        if not paths[name].is_dir():
            raise ValueError('Missing package directory: ' + name)
    for name in selected:
        steps = registry['implementations'][name].get('prepare', [])
        for index, step in enumerate(steps, 1):
            if 'if_exists' in step and not Path(expand(step['if_exists'], variables)).is_file():
                continue
            command = [expand(argument, variables) for argument in step['command']]
            label = f'{name} prepare {index}/{len(steps)} ({Path(command[0]).name})'
            process = run_streamed(label, command, expand(step['cwd'], variables),
                                   env=command_environment(name, variables, registry))
            errors = [line for line in process.stdout.splitlines()
                      if re.search(r'Permission denied|error:', line, re.IGNORECASE)]
            if process.returncode:
                failures.append(f'{label}: exit {process.returncode}: {" ".join(command)}')
            failures += [f'{label}: Build reported an error: {line}' for line in errors]
            if process.returncode or errors:
                failed.add(name)
                break  # The later steps of this implementation need this one.
            for line in process.stdout.splitlines():
                if re.search(r'warning:', line, re.IGNORECASE):
                    for repository, path in sorted(paths.items(), key=lambda item: -len(str(item[1]))):
                        line = line.replace(str(path) + '/', repository + '/')
                    warnings.append({'implementation': name, 'message': line})
    if failures:
        raise Failures(failures, failed)
    return warnings


def adapter_commands(selected, paths, cache, registry=REGISTRY):
    variables = context(paths, cache)
    return {name: [expand(argument, variables) for argument in registry['implementations'][name]['command']]
            for name in selected}


def declared_commands(key, selected, paths, cache, registry=REGISTRY):
    """Resolve a declared per-package command, keeping the declared form for records."""
    variables = context(paths, cache)
    result = {}
    for name in selected:
        declaration = registry['implementations'][name].get(key)
        if declaration is not None:
            result[name] = {'cwd': expand(declaration['cwd'], variables),
                            'command': [expand(argument, variables) for argument in declaration['command']],
                            'declared': list(declaration['command'])}
            if 'format' in declaration:
                result[name]['format'] = declaration['format']
            environment = command_environment(name, variables, registry)
            if environment is not None:
                result[name]['env'] = environment
    return result


def test_commands(selected, paths, cache, registry=REGISTRY):
    """Resolve each declared package test command."""
    return declared_commands('tests', selected, paths, cache, registry)


def case_commands(selected, paths, cache, registry=REGISTRY):
    """Resolve each declared command that lists the package test cases."""
    return declared_commands('test_cases', selected, paths, cache, registry)


def api_commands(selected, paths, cache, registry=REGISTRY):
    """Resolve each declared command that lists the public API symbols."""
    return declared_commands('api_symbols', selected, paths, cache, registry)


def runtime_versions(selected, paths, cache, registry=REGISTRY):
    """The runtime versions of every selected implementation; Failures names every command that
    failed or printed nothing, after all ran."""
    variables = context(paths, cache)
    result, failures, failed = {}, [], set()
    for name in selected:
        result[name] = {}
        for key, command in registry['implementations'][name]['runtime'].items():
            resolved = [expand(argument, variables) for argument in command]
            # The repository directory selects the toolchain that its pin files name.
            repository = paths[registry['implementations'][name]['repository']]
            try:
                value = subprocess.check_output(resolved, cwd=repository, text=True, stderr=subprocess.PIPE,
                                                env=command_environment(name, variables, registry)).strip()
            except subprocess.CalledProcessError as error:
                failures.append(f'{name}/{key}: {" ".join(resolved)} failed with exit {error.returncode}: '
                                f'{(error.stderr or "").strip() or (error.stdout or "").strip() or "no output"}')
                failed.add(name)
                continue
            except OSError as error:
                failures.append(f'{name}/{key}: {" ".join(resolved)} failed: {error}')
                failed.add(name)
                continue
            if not value:
                failures.append('Runtime version is empty: ' + name + '/' + key)
                failed.add(name)
                continue
            result[name][key] = value
    if failures:
        raise Failures(failures, failed)
    return result


def parse_overrides(arguments):
    result = {}
    for argument in arguments or []:
        name, separator, path = argument.partition('=')
        if not separator or not path or name in result:
            raise ValueError('Use one --repository NAME=PATH per repository')
        result[name] = Path(path)
    return result

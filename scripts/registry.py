"""Load implementation commands and resolve monorepo package paths."""
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def load_registry(root=ROOT):
    registry = json.loads((root / 'implementations.json').read_text())
    if registry.get('schema_version') != 1:
        raise ValueError('Unsupported implementation registry schema')
    repositories, implementations = registry['repositories'], registry['implementations']
    if not repositories or not implementations:
        raise ValueError('The registry requires repositories and implementations')
    for name, repository in repositories.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
            raise ValueError('Invalid repository name: ' + name)
        path = Path(repository['path'])
        if path.is_absolute() or '..' in path.parts or str(path) == '.':
            raise ValueError('Repository paths must be relative child directories')
        if repository['url'] != 'https://github.com/polyspec/ordered-json.git':
            raise ValueError('Package URLs must use the polyspec/ordered-json monorepo')
    for name, implementation in implementations.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
            raise ValueError('Invalid implementation name: ' + name)
        required = [implementation['repository']] + implementation.get('dependencies', [])
        if any(repository not in repositories for repository in required):
            raise ValueError('Implementation references an unknown repository: ' + name)
        commands = [implementation['command']] + list(implementation['runtime'].values())
        commands += [step['command'] for step in implementation.get('prepare', [])]
        if any(not command or not isinstance(command, list) or
               any(not isinstance(argument, str) for argument in command) for command in commands):
            raise ValueError('Commands must be nonempty argument lists: ' + name)
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


def prepare(selected, paths, cache, registry=REGISTRY):
    variables = context(paths, cache)
    warnings = []
    for name in required_repositories(selected, registry):
        if not paths[name].is_dir():
            raise ValueError('Missing repository checkout: ' + name)
    for name in selected:
        for step in registry['implementations'][name].get('prepare', []):
            if 'if_exists' in step and not Path(expand(step['if_exists'], variables)).is_file():
                continue
            command = [expand(argument, variables) for argument in step['command']]
            process = subprocess.run(command, cwd=expand(step['cwd'], variables), text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            print(process.stdout, end='', flush=True)
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, command)
            for line in process.stdout.splitlines():
                if re.search(r'Permission denied|error:', line, re.IGNORECASE):
                    raise RuntimeError('Build reported an error: ' + line)
                if re.search(r'warning:', line, re.IGNORECASE):
                    for repository, path in sorted(paths.items(), key=lambda item: -len(str(item[1]))):
                        line = line.replace(str(path) + '/', repository + '/')
                    warnings.append({'implementation': name, 'message': line})
    return warnings


def adapter_commands(selected, paths, cache, registry=REGISTRY):
    variables = context(paths, cache)
    return {name: [expand(argument, variables) for argument in registry['implementations'][name]['command']]
            for name in selected}


def runtime_versions(selected, paths, cache, registry=REGISTRY):
    variables = context(paths, cache)
    result = {}
    for name in selected:
        result[name] = {}
        for key, command in registry['implementations'][name]['runtime'].items():
            value = subprocess.check_output([expand(argument, variables) for argument in command],
                                            text=True, stderr=subprocess.PIPE).strip()
            if not value:
                raise ValueError('Runtime version is empty: ' + name + '/' + key)
            result[name][key] = value
    return result


def parse_overrides(arguments):
    result = {}
    for argument in arguments or []:
        name, separator, path = argument.partition('=')
        if not separator or not path or name in result:
            raise ValueError('Use one --repository NAME=PATH per repository')
        result[name] = Path(path)
    return result

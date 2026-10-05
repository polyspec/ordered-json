#!/usr/bin/env python3
"""Run the owning checks of changed paths, and check that every tracked path has an owner.

    python3 scripts/owner_check.py                    the owners of the uncommitted changes and untracked files
    python3 scripts/owner_check.py --paths "A B"      the owners of the paths A and B
    python3 scripts/owner_check.py --base REV         the owners of the paths changed since REV
    python3 scripts/owner_check.py --dry-run          print the selection as JSON without running it
    python3 scripts/owner_check.py --validate         check the map only (the pre-commit hook)

scripts/owner-checks.json maps globs of repository paths to their owners: verifier unit test modules
of scripts/tests, implementations that scripts/verify.py --only builds and checks, and the checks docs
and benchmark. `make owner-check` runs exactly the owners of the changed paths, never the full run,
which make check runs once when every active item is complete. The map is checked before any owner
runs: every tracked path matches a rule, every glob matches a tracked path, and every owner exists;
the pre-commit hook .githooks/pre-commit runs that check, so a commit with an unmapped path fails.
Every owner runs to its end and every failure is listed before the command exits with status 1.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = 'scripts/owner-checks.json'
CHECKS = ('docs', 'benchmark')


def glob_source(glob):
    """The regular expression source of a glob: * within a segment, ** across segments, {a,b}."""
    source, index = '', 0
    while index < len(glob):
        if glob.startswith('**/', index):
            source, index = source + '(?:.*/)?', index + 3
        elif glob.startswith('**', index):
            source, index = source + '.*', index + 2
        elif glob[index] == '*':
            source, index = source + '[^/]*', index + 1
        elif glob[index] == '{':
            end = glob.index('}', index)
            source += '(?:' + '|'.join(glob_source(part) for part in glob[index + 1:end].split(',')) + ')'
            index = end + 1
        else:
            source, index = source + re.escape(glob[index]), index + 1
    return source


def matches(glob, path):
    return re.fullmatch(glob_source(glob), path) is not None


def implementations(root):
    return list(json.loads((Path(root) / 'implementations.json').read_text())['implementations'])


def validate(declaration, tracked, root=ROOT):
    """The errors of the map against the tracked paths: unmapped paths, dead globs, unknown owners."""
    errors, known = [], implementations(root)
    for rule in declaration['owners']:
        where = ' '.join(rule['paths'])
        for glob in rule['paths']:
            if not any(matches(glob, path) for path in tracked):
                errors.append(f'{DECLARATION}: the glob {glob} matches no tracked path')
        for test in rule.get('tests', []):
            if test != '$module' and not (Path(root) / 'scripts/tests' / f'{test}.py').is_file():
                errors.append(f'{DECLARATION}: the test module {test} of {where} is not a file of scripts/tests')
        for language in rule.get('languages', []):
            if language != '*' and language not in known:
                errors.append(f'{DECLARATION}: the language {language} of {where} is not an implementation')
        for check in rule.get('checks', []):
            if check not in CHECKS:
                errors.append(f'{DECLARATION}: the check {check} of {where} is not {" or ".join(CHECKS)}')
    for path in tracked:
        if not any(matches(glob, path) for rule in declaration['owners'] for glob in rule['paths']):
            errors.append(f'{path}: the path matches no owner in {DECLARATION}')
    return errors


def select(declaration, changed, exists, root=ROOT):
    """The owners of the changed paths. A removed path that no rule owns selects nothing; an existing
    path that no rule owns is unowned."""
    known = implementations(root)
    tests, languages, checks, unowned, reasons = set(), set(), set(), [], []
    for path in changed:
        rules = [rule for rule in declaration['owners'] if any(matches(glob, path) for glob in rule['paths'])]
        if not rules:
            if exists(path):
                unowned.append(path)
            else:
                reasons.append(f'{path}: removed, and no rule owns it')
            continue
        for rule in rules:
            for test in rule.get('tests', []):
                if test != '$module':
                    tests.add(test)
                elif exists(path):
                    tests.add(Path(path).stem)
            languages.update(known if '*' in rule.get('languages', []) else rule.get('languages', []))
            checks.update(rule.get('checks', []))
        reasons.append(f'{path}: {len(rules)} rule{"" if len(rules) == 1 else "s"}')
    return {'tests': sorted(tests), 'languages': [name for name in known if name in languages],
            'checks': [check for check in CHECKS if check in checks], 'unowned': unowned, 'reasons': reasons}


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.split('\n')


def changed_paths(arguments):
    if arguments.paths is not None:
        return sorted(set(arguments.paths.split()))
    changed = git('diff', '--name-only', arguments.base or 'HEAD')
    return sorted(set(filter(None, changed + git('ls-files', '--others', '--exclude-standard'))))


def step(name, command):
    print(f'[owner-check] start {name}', flush=True)
    started = time.monotonic()
    status = subprocess.run(command, cwd=ROOT).returncode
    print(f'[owner-check] {name} {"passed" if status == 0 else f"failed with exit {status}"} in '
          f'{time.monotonic() - started:.1f} s', flush=True)
    return status == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--paths')
    parser.add_argument('--base')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--validate', action='store_true')
    arguments = parser.parse_args(argv)
    declaration = json.loads((ROOT / DECLARATION).read_text())
    errors = validate(declaration, [name for name in git('ls-files', '--cached') if name], ROOT)
    for error in errors:
        print(f'[owner-check] {error}', file=sys.stderr)
    if errors:
        return 1
    if arguments.validate:
        print(f'[owner-check] {DECLARATION} owns every tracked path')
        return 0
    selection = select(declaration, changed_paths(arguments), lambda path: (ROOT / path).exists())
    for path in selection['unowned']:
        print(f'[owner-check] {path}: the path matches no owner in {DECLARATION}', file=sys.stderr)
    if selection['unowned']:
        return 1
    if arguments.dry_run:
        print(json.dumps(selection, indent=2))
        return 0
    commands = []
    if selection['tests']:
        commands.append(('unit tests ' + ' '.join(selection['tests']),
                         [sys.executable, 'scripts/test.py', '--unit', *selection['tests']]))
    if 'docs' in selection['checks']:
        commands.append(('docs', [sys.executable, 'scripts/docs_check.py']))
    if selection['languages']:
        only = [argument for language in selection['languages'] for argument in ('--only', language)]
        commands.append(('verify ' + ' '.join(selection['languages']), [sys.executable, 'scripts/verify.py', *only]))
    if 'benchmark' in selection['checks']:
        commands.append(('benchmark', [sys.executable, 'benchmarks/run.py', '--check']))
    failed = [name for name, command in commands if not step(name, command)]
    if failed:
        print(f'[owner-check] failed: {"; ".join(failed)}', file=sys.stderr)
        return 1
    print(f'[owner-check] {len(commands)} owner checks passed' if commands else '[owner-check] no owner selected')
    return 0


if __name__ == '__main__':
    sys.exit(main())

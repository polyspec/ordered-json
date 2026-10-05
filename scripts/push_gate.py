#!/usr/bin/env python3
"""Refuse a push while a feature of docs/features.md is partial or a task of the execution checklist is [~].

    python3 scripts/push_gate.py hook           the pre-push hook: the pushed commits and the working tree
    python3 scripts/push_gate.py commit <rev>   CI: one commit and its tracked pre-push hook
    python3 scripts/push_gate.py hooks-check    the pre-push hook is installed in this checkout
    python3 scripts/push_gate.py hooks-install  make hooks: set core.hooksPath when it differs, then hooks-check

A push happens only when no feature is partial and no task is in progress (AGENTS). The pre-push hook .githooks/pre-push runs the
`hook` mode with the lines that Git writes to it, `<local ref> <local sha> <remote ref> <remote sha>`,
and refuses the push when the docs/features.md of a pushed commit or of the working tree has a
partial feature or its docs/plans/execution-checklist.md has a task in state [~], naming each one. `make hooks` runs `hooks-install`, which sets core.hooksPath to
.githooks when it differs, and `hooks-check` fails when it is not set or the hook is not executable. The workflow .github/workflows/push-gate.yml
runs the `commit` mode on every pushed commit and pull request, because a push from a checkout
without the hook does not run it. The partial features and the tasks in progress are those of the guard scripts/full_run.py.
Every mode refuses when it cannot read what it checks.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

from full_run import ACTIVE_STATE, CHECKLIST, FEATURES, TASK_ACTIVE, active_items, active_tasks

HOOKS_PATH = '.githooks'
HOOK = '.githooks/pre-push'
# The commit-time check: scripts/owner_check.py --validate refuses a commit with an unmapped path.
HOOKS = (HOOK, '.githooks/pre-commit')
SHORT = 12
RULE = ('A push happens only when no feature is partial and no task is in progress (AGENTS.md): work in progress '
        'does not reach the remote, where hosted CI runs the full suite on every pushed commit of main and every pull '
        'request.')
FIX = ('Complete each feature and set its implementation to implemented, and complete each task and set it to [o], '
       'in a commit with its documentation, tests and changelog entry; then push again.')


class Refusal(Exception):
    """A push is refused for a reason other than a partial feature."""


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise Refusal(f"git {' '.join(args)} exited with {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def committed_text(root, commit, where, name):
    result = subprocess.run(['git', 'show', f'{commit}:{name}'], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise Refusal(f'cannot read {name} of {where}: {result.stderr.strip()}')
    return result.stdout


def committed_items(root, commit, where):
    """The partial features of docs/features.md and the tasks in progress of the execution checklist in a
    commit, as two lists; `where` names the commit in a refusal."""
    features = active_items(committed_text(root, commit, where, FEATURES))
    return features, active_tasks(committed_text(root, commit, where, CHECKLIST))


def working_items(root):
    found = []
    for name, read in ((FEATURES, active_items), (CHECKLIST, active_tasks)):
        path = Path(root) / name
        if not path.is_file():
            raise Refusal(f'cannot read {name} of the working tree: {path} does not exist')
        found.append(read(path.read_text()))
    return found


def in_progress(found, tasks=()):
    """The refusal for `found` and `tasks`, lists of (where, item) pairs of partial features and tasks in progress."""
    lines = []
    if found:
        lines += [f'push refused: features are in progress (implementation {ACTIVE_STATE}, {FEATURES})']
        lines += [f"  {where}: {item['id']} {item['title']}" for where, item in found]
    if tasks:
        lines += [f'push refused: tasks are in progress ({TASK_ACTIVE}, {CHECKLIST})']
        lines += [f"  {where}: {item['id']} {item['title']}" for where, item in tasks]
    return lines + [RULE, FIX]


def hooks_issue(root):
    """Why the pre-push hook is not installed in the checkout `root`, or None."""
    result = subprocess.run(['git', 'config', 'core.hooksPath'], cwd=root, capture_output=True, text=True)
    configured = result.stdout.strip()
    if configured != HOOKS_PATH:
        shown = configured or 'unset'
        return f'core.hooksPath is {shown}, not {HOOKS_PATH}; run make hooks'
    for name in HOOKS:
        hook = Path(root) / name
        if not (hook.is_file() and os.access(hook, os.X_OK)):
            return f'{name} is missing or not executable; restore it with git checkout -- {name}'
    return None


def hook(root, lines):
    """The refusal lines for the pushed refs of the pre-push input `lines`, or [] to allow the push."""
    try:
        found, tasks = [], []
        for line in lines:
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) != 4:
                raise Refusal(f'the pre-push input line {line.strip()!r} is not <local ref> <local sha> <remote ref> <remote sha>')
            local_sha, remote_ref = fields[1], fields[2]
            if re.fullmatch(r'0+', local_sha):
                continue  # A deletion pushes no tree.
            where = f'{remote_ref} {local_sha[:SHORT]}'
            features, active = committed_items(root, local_sha, where)
            found += [(where, item) for item in features]
            tasks += [(where, item) for item in active]
        features, active = working_items(root)
        found += [('working tree', item) for item in features]
        tasks += [('working tree', item) for item in active]
    except (Refusal, OSError, ValueError, IndexError) as cause:
        return [f'push refused: {cause}', RULE]
    return in_progress(found, tasks) if found or tasks else []


def commit(root, revision):
    """The commit of `revision` and its refusal lines for CI, [] when it passes."""
    sha = revision
    try:
        sha = git(root, 'rev-parse', '--verify', f'{revision}^{{commit}}').strip()
        features, active = committed_items(root, sha, sha[:SHORT])
        found = [(sha[:SHORT], item) for item in features]
        tasks = [(sha[:SHORT], item) for item in active]
        modes = {}
        for name in HOOKS:
            entry = git(root, 'ls-tree', sha, '--', name).split()
            modes[name] = entry[0] if entry else None
    except (Refusal, OSError, ValueError, IndexError) as cause:
        return sha, [f'push refused: {cause}', RULE]
    lines = in_progress(found, tasks) if found or tasks else []
    for name, mode in reversed(list(modes.items())):
        if mode != '100755':
            lines = [f"push refused: {name} is not tracked with mode 100755 in {sha[:SHORT]} "
                     f"({f'mode {mode}' if mode else 'not tracked'}); every checkout runs it as a hook"] + lines
    return sha, lines


def report_ci(lines):
    for line in lines:
        print(f'::error::{line}')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as stream:
            stream.write('```\n' + '\n'.join(lines) + '\n```\n')


def main(argv):
    try:
        root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').strip())
    except Refusal as cause:
        print(f'push refused: {cause}', file=sys.stderr)
        return 1
    if argv == ['hook']:
        lines = hook(root, sys.stdin.read().splitlines())
    elif len(argv) == 2 and argv[0] == 'commit':
        sha, lines = commit(root, argv[1])
        if lines:
            report_ci(lines)
        else:
            print(f'push gate: no feature is {ACTIVE_STATE} and no task is {TASK_ACTIVE} in {sha[:SHORT]}; {" and ".join(HOOKS)} are tracked with mode 100755')
    elif argv == ['hooks-install']:
        configured = subprocess.run(['git', 'config', 'core.hooksPath'], cwd=root, capture_output=True,
                                    text=True).stdout.strip()
        if configured != HOOKS_PATH:
            git(root, 'config', 'core.hooksPath', HOOKS_PATH)
            print(f'hooks-install: core.hooksPath set to {HOOKS_PATH} (was {configured or "unset"})')
        issue = hooks_issue(root)
        lines = [f'the pre-push hook is not installed: {issue}'] if issue else []
        if not lines:
            print(f'hooks-check: core.hooksPath is {HOOKS_PATH} and {" and ".join(HOOKS)} are executable')
    elif argv == ['hooks-check']:
        issue = hooks_issue(root)
        lines = [f'the pre-push hook is not installed: {issue}'] if issue else []
        if not lines:
            print(f'hooks-check: core.hooksPath is {HOOKS_PATH} and {" and ".join(HOOKS)} are executable')
    else:
        print(__doc__, file=sys.stderr)
        return 2
    for line in lines:
        print(line, file=sys.stderr)
    return 1 if lines else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

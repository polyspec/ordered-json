#!/usr/bin/env python3
"""Refuse a push while a feature of docs/features.md is partial.

    python3 scripts/push_gate.py hook           the pre-push hook: the pushed commits and the working tree
    python3 scripts/push_gate.py commit <rev>   CI: one commit and its tracked pre-push hook
    python3 scripts/push_gate.py hooks-check    the pre-push hook is installed in this checkout

A push happens only when no feature is partial (AGENTS). The pre-push hook .githooks/pre-push runs the
`hook` mode with the lines that Git writes to it, `<local ref> <local sha> <remote ref> <remote sha>`,
and refuses the push when the docs/features.md of a pushed commit or of the working tree has a
partial feature, naming each one. Every make run sets core.hooksPath to .githooks, and `hooks-check`
fails when it is not set or the hook is not executable. The workflow .github/workflows/push-gate.yml
runs the `commit` mode on every pushed commit and pull request, because a push from a checkout
without the hook does not run it. The partial features are those of the guard scripts/full_run.py.
Every mode refuses when it cannot read what it checks.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

from full_run import ACTIVE_STATE, FEATURES, active_items

HOOKS_PATH = '.githooks'
HOOK = '.githooks/pre-push'
SHORT = 12
RULE = ('A push happens only when no feature is partial (AGENTS.md): CI runs the full verification on the pushed '
        'tree, and its guard refuses a tree with a feature in progress.')
FIX = ('Complete each feature and set its implementation to implemented in a commit with its documentation, '
       'tests and changelog entry; then push again.')


class Refusal(Exception):
    """A push is refused for a reason other than a partial feature."""


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise Refusal(f"git {' '.join(args)} exited with {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def committed_items(root, commit, where):
    """The partial features of docs/features.md in a commit; `where` names the commit in a refusal."""
    result = subprocess.run(['git', 'show', f'{commit}:{FEATURES}'], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise Refusal(f'cannot read {FEATURES} of {where}: {result.stderr.strip()}')
    return active_items(result.stdout)


def working_items(root):
    path = Path(root) / FEATURES
    if not path.is_file():
        raise Refusal(f'cannot read {FEATURES} of the working tree: {path} does not exist')
    return active_items(path.read_text())


def in_progress(found):
    """The refusal for `found`, a list of (where, feature) pairs."""
    lines = [f'push refused: features are in progress (implementation {ACTIVE_STATE}, {FEATURES})']
    lines += [f"  {where}: {item['id']} {item['title']}" for where, item in found]
    return lines + [RULE, FIX]


def hooks_issue(root):
    """Why the pre-push hook is not installed in the checkout `root`, or None."""
    result = subprocess.run(['git', 'config', 'core.hooksPath'], cwd=root, capture_output=True, text=True)
    configured = result.stdout.strip()
    if configured != HOOKS_PATH:
        shown = configured or 'unset'
        return f'core.hooksPath is {shown}, not {HOOKS_PATH}; run make hooks (every make run sets it)'
    hook = Path(root) / HOOK
    if not (hook.is_file() and os.access(hook, os.X_OK)):
        return f'{HOOK} is missing or not executable; restore it with git checkout -- {HOOK}'
    return None


def hook(root, lines):
    """The refusal lines for the pushed refs of the pre-push input `lines`, or [] to allow the push."""
    try:
        found = []
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
            found += [(where, item) for item in committed_items(root, local_sha, where)]
        found += [('working tree', item) for item in working_items(root)]
    except (Refusal, OSError, ValueError, IndexError) as cause:
        return [f'push refused: {cause}', RULE]
    return in_progress(found) if found else []


def commit(root, revision):
    """The commit of `revision` and its refusal lines for CI, [] when it passes."""
    sha = revision
    try:
        sha = git(root, 'rev-parse', '--verify', f'{revision}^{{commit}}').strip()
        found = [(sha[:SHORT], item) for item in committed_items(root, sha, sha[:SHORT])]
        entry = git(root, 'ls-tree', sha, '--', HOOK).split()
        mode = entry[0] if entry else None
    except (Refusal, OSError, ValueError, IndexError) as cause:
        return sha, [f'push refused: {cause}', RULE]
    lines = in_progress(found) if found else []
    if mode != '100755':
        lines = [f"push refused: {HOOK} is not tracked with mode 100755 in {sha[:SHORT]} "
                 f"({f'mode {mode}' if mode else 'not tracked'}); every checkout runs it as its pre-push hook"] + lines
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
            print(f'push gate: no feature is {ACTIVE_STATE} in {sha[:SHORT]}; {HOOK} is tracked with mode 100755')
    elif argv == ['hooks-check']:
        issue = hooks_issue(root)
        lines = [f'the pre-push hook is not installed: {issue}'] if issue else []
        if not lines:
            print(f'hooks-check: core.hooksPath is {HOOKS_PATH} and {HOOK} is executable')
    else:
        print(__doc__, file=sys.stderr)
        return 2
    for line in lines:
        print(line, file=sys.stderr)
    return 1 if lines else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

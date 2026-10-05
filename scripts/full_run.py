#!/usr/bin/env python3
"""Guard the full run: once per committed tree, when no feature is in progress.

    python3 scripts/full_run.py run -- <command>...   run the full verification command
    python3 scripts/full_run.py rerun-failed          rerun the targets of the current tree that did not pass

`make check` and `make rerun-failed` start this guard before any step. The full run happens once,
after every active item is complete (AGENTS). The active work of this repository is a feature row
of docs/features.md whose implementation state is `partial`. The guard refuses a run while such a
row exists, while the pre-push hook of scripts/push_gate.py is not installed in the checkout, while
tracked changes are uncommitted, while docs/pie-verification.json fails the check
that the documentation check of the verification applies to it, and while the run of another process
is still going on. A full run is refused when var/full-run.json already records a run of the current tree
(`git rev-parse HEAD^{tree}`); `rerun-failed` is refused unless that record exists and has targets
that did not pass. The guard prints its decision with the reason, runs each target to its end,
prints its start and its result with the elapsed time, and writes the record before and after each
target, so a run that is stopped stays recorded as `incomplete`. No step has a time limit.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

from docs_check import check_pie_verification

ROOT = Path(__file__).resolve().parents[1]
FEATURES = 'docs/features.md'
# The record of the last full run of this checkout; /var/ is ignored by Git.
RECORD = 'var/full-run.json'
ACTIVE_STATE = 'partial'
# Written by make pie-check; the documentation check at the end of the verification rejects it when
# it is stale.
PIE_RECORD = 'docs/pie-verification.json'


def active_items(text):
    """The feature rows whose implementation state is `partial`, with their feature text as title."""
    items = []
    for line in text.splitlines():
        if not re.match(r'^\|\s*F-', line):
            continue
        # A cell may contain an escaped `\|`.
        cells = [cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
        if cells[2] == ACTIVE_STATE:
            items.append({'id': cells[0], 'title': cells[1]})
    return items


def not_passed(record):
    return [target for target in record['targets'] if target['status'] != 'passed']


def names(targets):
    return ', '.join(target['name'] for target in targets)


def pie_issue(root):
    """Why the documentation check of the verification would reject the PIE record, or None."""
    path = Path(root) / PIE_RECORD
    if not path.exists():
        return None
    try:
        check_pie_verification(Path(root), json.loads(path.read_text()))
    except (ValueError, KeyError) as issue:
        return str(issue)
    return None


def decide(mode, targets, active, hooks, dirty, pie, tree, record, running):
    """Decide whether the guard runs; returns {'run', 'reason', 'targets'}.

    `active` holds the partial features, `hooks` why the pre-push hook is not installed or None, `dirty` the `git status --porcelain` lines of tracked
    files, `pie` why the PIE record would fail the documentation check or None, `record` the record
    of the last run or None, and `running` whether the process of an incomplete record still exists.
    """
    def refuse(reason):
        return {'run': False, 'reason': reason, 'targets': []}

    if active:
        plural = '' if len(active) == 1 else 's'
        listed = '\n'.join(f"  {item['id']} {item['title']}" for item in active)
        return refuse(f'{len(active)} active feature{plural} (implementation {ACTIVE_STATE}) in {FEATURES}; '
                      f'the full run happens once, when every active item is complete:\n{listed}')
    if hooks:
        return refuse(f'the pre-push hook is not installed: {hooks}')
    if dirty:
        listed = '\n'.join(f'  {line}' for line in dirty)
        return refuse(f'the working tree has uncommitted tracked changes; a full run verifies a committed tree; '
                      f'commit them, then run make check again; make pie-check writes {PIE_RECORD}, which is '
                      f'committed by itself before make check (AGENTS):\n{listed}')
    if pie:
        return refuse(f'{PIE_RECORD} would fail the documentation check at the end of the verification: {pie}; '
                      f'run make pie-check PIE=/path/to/pie.phar with the supplementary suite once, commit '
                      f'{PIE_RECORD} by itself, then run make check (AGENTS)')
    if record and running:
        return refuse(f"the run started {record['started']} by process {record['pid']} is still running on tree {record['tree']}")
    if mode == 'run':
        if record and record['tree'] == tree:
            remaining = not_passed(record)
            rerun = f'; make rerun-failed reruns its targets that did not pass: {names(remaining)}' if remaining else ''
            return refuse(f"the full run of tree {tree} (commit {record['commit']}) started {record['started']} "
                          f"with result {record['result']}; the full run happens once per tree{rerun}")
        if record:
            before = (f"tree {tree} differs from the tree {record['tree']} of the last full run "
                      f"(result {record['result']}, started {record['started']})")
        else:
            before = f'no full-run record in {RECORD} for tree {tree}'
        return {'run': True, 'reason': f'{before}; no active feature; {len(targets)} target{"" if len(targets) == 1 else "s"}',
                'targets': targets}
    if not record:
        return refuse(f'no full-run record in {RECORD}; rerun-failed reruns the targets of a full run '
                      'of the current tree that did not pass')
    if record['tree'] != tree:
        return refuse(f"the last full run (started {record['started']}) verified tree {record['tree']}, "
                      f'not the current tree {tree}; rerun-failed reruns only targets of the current tree')
    remaining = not_passed(record)
    if not remaining:
        return refuse(f"the full run of tree {tree} started {record['started']} passed; no target failed")
    return {'run': True, 'reason': f"the full run of tree {tree} started {record['started']} has {len(remaining)} "
                                   f"target{'' if len(remaining) == 1 else 's'} that did not pass: {names(remaining)}",
            'targets': remaining}


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout


def read_record(root):
    path = Path(root) / RECORD
    return json.loads(path.read_text()) if path.exists() else None


def write_record(root, record):
    path = Path(root) / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'{path.name}.{os.getpid()}')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.replace(path)


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists and belongs to another user.
        return True
    return True


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def run_command(root, target):
    """Run the command of a target in the checkout with its output; return whether it ended with status 0."""
    return subprocess.run(target['command'], cwd=root).returncode == 0


def full_run(root, mode, targets, run_target=None, print_line=print):
    """Inspect the checkout, decide and run; return 0 when the full result of the tree is passed."""
    root = Path(root)
    run_target = run_target or (lambda target: run_command(root, target))
    from push_gate import hooks_issue  # push_gate imports this module for its parser.
    active = active_items((root / FEATURES).read_text())
    hooks = hooks_issue(root)
    dirty = [line for line in git(root, 'status', '--porcelain', '--untracked-files=no').splitlines() if line]
    tree = git(root, 'rev-parse', 'HEAD^{tree}').strip()
    commit = git(root, 'rev-parse', 'HEAD').strip()
    record = read_record(root)
    running = bool(record and record['result'] == 'incomplete' and record.get('pid') != os.getpid() and alive(record['pid']))
    pie = None if dirty else pie_issue(root)
    decision = decide(mode, targets, active, hooks, dirty, pie, tree, record, running)
    print_line(f"[full-run] {'run' if decision['run'] else 'refuse'}: {decision['reason']}")
    if not decision['run']:
        return 1

    if mode == 'run':
        current = {'tree': tree, 'commit': commit, 'result': 'incomplete', 'pid': os.getpid(), 'started': now(),
                   'ended': None, 'targets': [{'name': target['name'], 'command': target['command'], 'status': 'pending'}
                                              for target in targets], 'reruns': []}
        rerun = None
    else:
        current = {**record, 'result': 'incomplete', 'pid': os.getpid()}
        rerun = {'started': now(), 'ended': None, 'targets': [target['name'] for target in decision['targets']],
                 'result': 'incomplete'}
        current['reruns'].append(rerun)
    write_record(root, current)

    begin = time.monotonic()
    selected = [target['name'] for target in decision['targets']]
    for index, name in enumerate(selected):
        target = next(entry for entry in current['targets'] if entry['name'] == name)
        target.update(status='running', started=now(), ended=None, elapsedMs=None)
        write_record(root, current)
        print_line(f'[full-run] start {name} ({index + 1}/{len(selected)})')
        target_begin = time.monotonic()
        passed = run_target(target)
        target.update(status='passed' if passed else 'failed', ended=now(),
                      elapsedMs=round((time.monotonic() - target_begin) * 1000))
        write_record(root, current)
        print_line(f"[full-run] {name} {target['status']} in {target['elapsedMs'] / 1000:.1f} s")

    failed = [target['name'] for target in current['targets'] if target['status'] == 'failed']
    current.update(result='passed' if not failed else 'failed', failed=failed, ended=now())
    if rerun:
        rerun.update(ended=current['ended'], result='passed' if not set(selected) & set(failed) else 'failed')
    write_record(root, current)
    summary = (f'{len([name for name in selected if name not in failed])} of {len(selected)} targets passed '
               f'in {time.monotonic() - begin:.1f} s')
    if failed:
        print_line(f"[full-run] result failed for tree {tree}: {summary}; failed: {', '.join(failed)}; make rerun-failed reruns them")
        return 1
    print_line(f'[full-run] result passed for tree {tree}: {summary}')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=['run', 'rerun-failed'])
    parser.add_argument('command', nargs=argparse.REMAINDER, help='after --: the full verification command of run')
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if (args.mode == 'run') != bool(command):
        parser.error('run requires the full verification command after --; rerun-failed takes none')
    targets = [{'name': shlex.join(command), 'command': command}] if command else []
    return full_run(ROOT, args.mode, targets, print_line=lambda line: print(line, flush=True))


if __name__ == '__main__':
    sys.exit(main())

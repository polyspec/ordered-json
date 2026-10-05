#!/usr/bin/env python3
"""Run the make targets of one CI job to their end and write the report of the job.

    python3 scripts/ci_run.py run --job JOB -- TARGET...   make ci: run each target, past failures
    python3 scripts/ci_run.py summary --job JOB            make ci-summary: the summary of the job

Hosted CI runs the full suite after a push (.github/workflows/ci.yml). A failure never stops the run: every
target of the job runs to its end, and every failure leaves a reason detailed enough to fix every failure
before the next run. `run` runs `make TARGET` for each target in order, prints its output as it arrives and
writes it to var/ci/JOB/logs/TARGET.log, and writes var/ci/JOB/summary.json with the status, the exit status
and the elapsed time of each target before and after each one, so a run that stops leaves the targets it did
not reach as `pending`. It exits with status 1 when a target failed. No target has a time limit.

`summary` writes var/ci/JOB/summary.md: each target with its status and its time, and for each failed
target the first failure lines of its log. It copies the records of the run (var/records) into
var/ci/JOB/records and appends the summary to the job summary of GitHub ($GITHUB_STEP_SUMMARY). It never
fails: a missing or unreadable summary.json, log or record is named in the summary, and the step exits with
status 0, so the report of a job whose runner stopped is still written and uploaded.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RECORDS = 'var/records'
# The first failure lines of a failed target: lines that state a failure, refusal or error.
FAILURE = re.compile(r'\b(FAIL|FAILED|ERROR|Error|error|failed|refuse|refused|mismatch|missing|stale|Traceback|'
                     r'differs?|expected)\b|^- |^make: \*\*\*')
FAILURE_LINES = 20


def report_directory(root, job):
    return Path(root) / 'var/ci' / job


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def write_json(path, data):
    """Write data completely to a file next to path and rename it over path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def run(root, job, targets, make=('make',), stream=None):
    """Run `make TARGET` for each target to its end; return 0 when every target passed."""
    stream = stream or sys.stdout
    report = report_directory(root, job)
    if report.exists():
        shutil.rmtree(report)
    (report / 'logs').mkdir(parents=True)
    summary = {'job': job, 'started': now(), 'ended': None,
               'targets': [{'name': name, 'status': 'pending'} for name in targets]}
    write_json(report / 'summary.json', summary)
    for index, target in enumerate(summary['targets']):
        log = report / 'logs' / f"{target['name']}.log"
        target.update(status='running', started=now(), log=log.relative_to(report).as_posix())
        write_json(report / 'summary.json', summary)
        stream.write(f"[ci] start {target['name']} ({index + 1}/{len(targets)})\n")
        stream.flush()
        begin = time.monotonic()
        with open(log, 'w', encoding='utf-8') as output:
            try:
                process = subprocess.Popen([*make, target['name']], cwd=root, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True, errors='replace')
                for line in process.stdout:
                    stream.write(line)
                    output.write(line)
                status = process.wait()
            except OSError as error:
                output.write(f'{" ".join(make)} {target["name"]} could not start: {error}\n')
                status = 'not started'
        target.update(status='passed' if status == 0 else 'failed', exit=status, ended=now(),
                      seconds=round(time.monotonic() - begin, 1))
        write_json(report / 'summary.json', summary)
        stream.write(f"[ci] {target['name']} {target['status']} in {target['seconds']} s\n")
        stream.flush()
    summary['ended'] = now()
    write_json(report / 'summary.json', summary)
    failed = [target['name'] for target in summary['targets'] if target['status'] != 'passed']
    stream.write(f"[ci] {job}: {len(targets) - len(failed)} of {len(targets)} targets passed"
                 + (f"; failed: {', '.join(failed)}\n" if failed else '\n'))
    return 1 if failed else 0


def failure_lines(log):
    """The first lines of a log that state a failure, or its last lines when none does."""
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
    matched = [line for line in lines if FAILURE.search(line)]
    return (matched or lines[-FAILURE_LINES:])[:FAILURE_LINES]


def summarize(root, job):
    """The Markdown summary of the job; every problem of the report is named in it, none is raised."""
    report = report_directory(root, job)
    lines = [f'## CI job {job}', '']
    try:
        summary = json.loads((report / 'summary.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        return lines + [f'The run of make ci wrote no readable {report.relative_to(root)}/summary.json: {error}. '
                        'The step make ci did not start or stopped before its first target.', '']
    targets = summary.get('targets', [])
    failed = [target for target in targets if target.get('status') != 'passed']
    lines += [f"{len(targets) - len(failed)} of {len(targets)} targets passed; started {summary.get('started')}, "
              f"ended {summary.get('ended') or 'not ended: the run stopped'}.", '',
              '| Target | Status | Exit | Time |', '| --- | --- | --- | --- |']
    for target in targets:
        seconds = target.get('seconds')
        lines.append(f"| `{target.get('name')}` | {target.get('status')} | {target.get('exit', '')} | "
                     f"{'' if seconds is None else f'{seconds} s'} |")
    lines.append('')
    for target in failed:
        lines += [f"### `{target.get('name')}` {target.get('status')}", '']
        if not target.get('log'):
            lines += ['The target did not start: the run stopped before it.', '']
            continue
        try:
            excerpt = failure_lines(report / target['log'])
        except OSError as error:
            lines += [f"The log {target['log']} cannot be read: {error}", '']
            continue
        lines += [f"First failure lines of `{target['log']}` (the report holds the whole log):", '', '```']
        lines += [line.replace('```', "'''") for line in excerpt] + ['```', '']
    return lines


def records(root, job):
    """Copy the records of the run into the report; the lines that name what was copied or is missing."""
    source, target = Path(root) / RECORDS, report_directory(root, job) / 'records'
    names = sorted(path.name for path in source.glob('*.json')) if source.is_dir() else []
    for name in names:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target / name)
    if not names:
        return [f'No record in {RECORDS}: no target of this job wrote one.', '']
    return [f'Records of this run in the report: {", ".join(f"records/{name}" for name in names)}.', '']


def summary(root, job, environ=os.environ):
    """make ci-summary: write summary.md, copy the records and append to the job summary; never fails."""
    report = report_directory(root, job)
    try:
        text = summarize(root, job)
    except Exception as error:  # The summary of a broken report still names why.
        text = [f'## CI job {job}', '', f'The summary could not be built: {type(error).__name__}: {error}', '']
    try:
        text += records(root, job)
    except Exception as error:
        text += [f'The records could not be copied: {type(error).__name__}: {error}', '']
    body = '\n'.join(text) + '\n'
    try:
        report.mkdir(parents=True, exist_ok=True)
        (report / 'summary.md').write_text(body, encoding='utf-8')
    except OSError as error:
        body += f'\nThe summary could not be written to {report}/summary.md: {error}\n'
    print(body, end='')
    if environ.get('GITHUB_STEP_SUMMARY'):
        try:
            with open(environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
                stream.write(body)
        except OSError as error:
            print(f'The job summary {environ["GITHUB_STEP_SUMMARY"]} could not be written: {error}')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=['run', 'summary'])
    parser.add_argument('--job', required=True)
    # The targets follow `--`; they are split off before parsing, because a remainder argument after the mode would
    # also take --job.
    argv = list(sys.argv[1:] if argv is None else argv)
    targets = argv[argv.index('--') + 1:] if '--' in argv else []
    args = parser.parse_args(argv[:argv.index('--')] if '--' in argv else argv)
    if not re.fullmatch(r'[a-z][a-z0-9-]*', args.job):
        parser.error(f'--job {args.job!r} is not a job name [a-z][a-z0-9-]*')
    if args.mode == 'run':
        if not targets:
            parser.error(f'make ci CI_JOB={args.job}: the job has no targets; the Makefile names them in CI_TARGETS_{args.job}')
        return run(ROOT, args.job, targets)
    return summary(ROOT, args.job)


if __name__ == '__main__':
    sys.exit(main())

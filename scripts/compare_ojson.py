#!/usr/bin/env python3
"""Compare existing ojson projects using the existing shared cases and goldens."""
import argparse
from email.parser import Parser
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from registry import run_streamed
from verification_record import write_record
from verify import ROOT, Adapter, milliseconds, prepare_cases, reference


def structure(tree):
    """Preserve all container positions and object names, including duplicates."""
    if tree[0] == 'object':
        return ['object', [[key, structure(child)] for key, child in tree[1]]]
    if tree[0] == 'array':
        return ['array', [structure(child) for child in tree[1]]]
    return [tree[0]]


def assess(expected, actual):
    result = {'acceptance_matches': expected['ok'] == actual['ok'], 'accepted': actual['ok']}
    if not expected['ok']:
        return result
    result['structure_order_matches'] = (actual.get('tree') is not None
        and structure(expected['tree']) == structure(actual['tree']))
    result['decoded_tree_matches'] = actual.get('tree') == expected['tree']
    result['strict_output'] = False
    result['encoded_tree_matches'] = False
    result['token_text_matches'] = False
    if 'output' in actual:
        try:
            output = reference(actual['output'].encode('utf-8'))
        except (ValueError, UnicodeError, RecursionError):
            pass
        else:
            result['strict_output'] = True
            result['encoded_tree_matches'] = output['tree'] == expected['tree']
            result['token_text_matches'] = output['compact'] == expected['compact']
    return result


def compile_erlang(erl, source, out):
    """Compile the Erlang modules, streaming the compiler output. A build has no time
    limit; its exit status and output decide the result."""
    out.mkdir(parents=True, exist_ok=True)
    # JSON strings are also valid Erlang strings for these filesystem paths.
    files = sorted(source.glob('src/*.erl')) + [ROOT / 'scripts/comparison/ojson_comparison.erl']
    expression = ('Files = ' + json.dumps([str(path) for path in files]) + ', '
        'Results = [compile:file(F, [report_errors, report_warnings, {outdir, ' + json.dumps(str(out))
        + '}]) || F <- Files], halt(case lists:all(fun({ok, _}) -> true; (_) -> false end, Results) '
        'of true -> 0; false -> 1 end).')
    process = run_streamed('erlang compile', [str(erl), '+S', '2:2', '-noshell', '-eval', expression], ROOT)
    if process.returncode:
        raise RuntimeError(f'Erlang compilation failed with exit {process.returncode}:\n' + process.stdout)
    return process.stdout.replace(str(source) + '/', 'erlang-ojson/').replace(str(ROOT) + '/', '')


def observe(project, command, cases):
    """Send one case at a time and read its reply under the per-case deadline of the
    shared verifier, printing each case with its elapsed time. The run has no limit."""
    adapter = Adapter(project, command)
    try:
        replies = []
        for name, path, _ in cases:
            line, elapsed = adapter.exchange(name, path)
            actual = json.loads(line)
            verdict = 'accepted' if actual.get('ok') else 'rejected'
            print(f'{project}: {name} {verdict} ({milliseconds(elapsed)})', flush=True)
            replies.append(actual)
        adapter.finish(len(cases))
    finally:
        adapter.stop()
    return replies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python-package', type=Path, default=ROOT / '.cache/comparison/ojson-0.1.0')
    parser.add_argument('--erlang-source', type=Path, default=ROOT / '.cache/comparison/erlang-ojson')
    parser.add_argument('--erl', type=Path)
    parser.add_argument('--suite', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/reports/ojson-comparison.json')
    args = parser.parse_args()
    args.python_package = args.python_package.resolve()
    args.erlang_source = args.erlang_source.resolve()
    if not (args.python_package / 'ojson/ojson.py').is_file():
        parser.error('Extract the ojson 0.1.0 source distribution before running')
    if args.erl:
        erl = args.erl.resolve()
    elif shutil.which('erl'):
        erl = Path(shutil.which('erl'))
    else:
        runtimes = sorted((ROOT / '.cache/comparison/runtime/erlang').glob('*/lib/erlang/bin/erl'))
        if not runtimes:
            parser.error('Provide an Erlang runtime with --erl')
        erl = runtimes[-1]
    # The compiled modules and the case files belong to this run alone.
    with tempfile.TemporaryDirectory(prefix='ojson-comparison-') as directory:
        beam = Path(directory) / 'probe-ebin'
        cases_directory = Path(directory) / 'cases'
        cases_directory.mkdir()
        warnings = compile_erlang(erl, args.erlang_source, beam)
        commit = subprocess.check_output(['git', '-C', str(args.erlang_source), 'rev-parse', 'HEAD'], text=True).strip()
        runtime = subprocess.check_output([str(erl), '+S', '2:2', '-noshell', '-eval',
            'io:format("~s", [erlang:system_info(system_version)]), halt().'], text=True).strip()
        metadata = Parser().parsestr((args.python_package / 'PKG-INFO').read_text())
        suite_commit = subprocess.check_output(['git', '-C', str(args.suite.resolve()), 'rev-parse', 'HEAD'],
            text=True).strip() if args.suite else None
        report = {'python_package': {'version': metadata['Version'], 'runtime': sys.version.split()[0],
                      'module_sha256': hashlib.sha256((args.python_package / 'ojson/ojson.py').read_bytes()).hexdigest()},
                  'erlang_package': {'commit': commit, 'runtime': runtime, 'compile_warnings': warnings},
                  'official_sha256': hashlib.sha256((ROOT / 'examples/official.json').read_bytes()).hexdigest(),
                  'suite_commit': suite_commit,
                  'case_source': 'examples/official.json + fixtures/ + optional JSONTestSuite', 'projects': {}}
        commands = {
            'pypi-ojson': [sys.executable, str(ROOT / 'scripts/comparison/python_ojson_probe.py'), str(args.python_package)],
            'erlang-ojson': [str(erl), '+S', '2:2', '-noshell', '-pa', str(beam), '-s', 'ojson_comparison', 'main', '-s', 'init', 'stop'],
        }
        cases, official_count = prepare_cases(cases_directory, args.suite.resolve() if args.suite else None)
        for project, command in commands.items():
            results = []
            for (name, _, expected), actual in zip(cases, observe(project, command, cases)):
                verdict = assess(expected, actual)
                row = {'case': name, **verdict}
                if name.startswith('official/'):
                    row['observed'] = actual
                elif not verdict['acceptance_matches']:
                    row['decode_error'] = actual.get('decode_error')
                results.append(row)
            official = results[:official_count]
            summary = {
                'cases': len(results), 'official_cases': official_count,
                'official_structure_order_matches': sum(r['structure_order_matches'] for r in official),
                'official_decoded_tree_matches': sum(r['decoded_tree_matches'] for r in official),
                'official_encoded_tree_matches': sum(r['encoded_tree_matches'] for r in official),
                'official_strict_outputs': sum(r['strict_output'] for r in official),
                'acceptance_matches': sum(r['acceptance_matches'] for r in results),
            }
            report['projects'][project] = {'summary': summary, 'cases': results}
            print(project + ': ' + json.dumps(summary), flush=True)
    write_record(args.output, report)
    print('Saved ' + str(args.output))


if __name__ == '__main__':
    main()

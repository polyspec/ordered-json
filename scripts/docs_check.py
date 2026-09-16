#!/usr/bin/env python3
"""Check bilingual documents, local links, feature state, and current evidence."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from verification_record import IMPLEMENTATIONS, package_revisions, sha256, source_manifest
from registry import REGISTRY, artifact_paths, repository_paths

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'overview', 'specification', 'state', 'operations', 'history', 'procedure', 'usage', 'report'}
IGNORED = {'.git', '.cache', 'node_modules', 'target', 'vendor', '__pycache__',
           'autom4te.cache', 'build', 'modules', '.libs', 'include'}
PRIVATE_PATH = re.compile(r'/(?:Users|home)/[^/\s"<>]+/')
ANCHOR = re.compile(r'<a\s+id="([a-z0-9][a-z0-9-]*)"\s*></a>')
INLINE_LINK = re.compile(r'!?\[[^\]\n]*\]\((<[^>\n]+>|[^\s()]+(?:\([^\s()]*\)[^\s()]*)*)(?:\s+"[^"]*")?\)')


def markdown_parts(text):
    """Return prose and fenced blocks so code examples are not treated as links."""
    prose, blocks, block = [], [], []
    fence = None
    language = ''
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                blocks.append((language, '\n'.join(block)))
                fence, block = None, []
            else:
                block.append(line)
        elif marker:
            fence, language = marker[1], marker[2].strip()
        else:
            prose.append(line)
    if fence:
        raise ValueError('Unclosed fenced code block')
    return '\n'.join(prose), blocks


def link_targets(prose):
    prose = re.sub(r'(`+)[^`]*?\1', '', prose)
    links = [match[1].strip('<>') for match in INLINE_LINK.finditer(prose)]
    definitions = {match[1].lower(): match[2].strip('<>') for match in re.finditer(
        r'^ {0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)', prose, re.MULTILINE)}
    links.extend(definitions.values())
    for match in re.finditer(r'\[([^\]\n]+)\]\[([^\]\n]*)\]', prose):
        identifier = (match[2] or match[1]).lower()
        if identifier not in definitions:
            raise ValueError('Undefined reference link: ' + identifier)
    links.extend(re.findall(r'<((?:https?://|mailto:)[^>]+)>', prose))
    links.extend(re.findall(r'\bhref="([^"]+)"', prose))
    if re.search(r'\]\(', INLINE_LINK.sub('', prose)):
        raise ValueError('Malformed or unsupported inline link')
    return links


def local_target(root, source, target):
    parts = urlsplit(target)
    if parts.scheme:
        if parts.scheme in ('http', 'https') and parts.netloc and not re.search(r'\s', target):
            return None
        if parts.scheme == 'mailto' and '@' in parts.path:
            return None
        raise ValueError('Invalid external link: ' + target)
    if parts.netloc or parts.query:
        raise ValueError('Local links cannot contain a host or query: ' + target)
    path = (source.parent / unquote(parts.path)).resolve() if parts.path else source.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError('Link escapes repository: ' + target) from error
    if not path.exists():
        raise ValueError('Missing link target: ' + target)
    if parts.fragment:
        if path.suffix != '.md':
            raise ValueError('Local anchors must target Markdown: ' + target)
        prose, _ = markdown_parts(path.read_text(encoding='utf-8'))
        if unquote(parts.fragment) not in ANCHOR.findall(prose):
            raise ValueError('Missing explicit anchor: ' + target)
    return path


def authored_markdown(root):
    paths = set()
    package_roots = {Path(entry['path']).parts[0] for entry in REGISTRY['repositories'].values()}
    for folder, directories, files in os.walk(root):
        relative = Path(folder).resolve().relative_to(Path(root).resolve())
        if root.resolve() == ROOT.resolve() and relative.parts and relative.parts[0] in package_roots:
            directories[:] = []
            continue
        directories[:] = [name for name in directories if name not in IGNORED
                          and not (Path(folder) / name / '.git').exists()]
        for name in files:
            if name.endswith('.md'):
                paths.add((Path(folder) / name).relative_to(root).as_posix())
    return paths


def feature_rows(text):
    rows = {}
    for line in text.splitlines():
        if not re.match(r'^\|\s*F-', line):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) != 7 or not re.fullmatch(r'F-[A-Z0-9-]+', cells[0]):
            raise ValueError('Feature rows require ID, feature, implementation, verification, evidence, distribution, specification')
        identifier, feature, implementation, verification, evidence, distribution, specification = cells
        if identifier in rows:
            raise ValueError('Duplicate feature ID: ' + identifier)
        if not feature or implementation not in ('implemented', 'partial', 'planned'):
            raise ValueError('Invalid implementation state: ' + identifier)
        if verification not in ('shared-suite', 'docs-tests', 'benchmark', 'not-verified'):
            raise ValueError('Invalid verification state: ' + identifier)
        if distribution not in ('source-only', 'not-distributed', 'published'):
            raise ValueError('Invalid distribution state: ' + identifier)
        if implementation != 'implemented' and verification != 'not-verified':
            raise ValueError('Incomplete features cannot claim completed verification: ' + identifier)
        evidence_links, specification_links = link_targets(evidence), link_targets(specification)
        if len(specification_links) != 1:
            raise ValueError('A feature requires one specification link: ' + identifier)
        if verification != 'not-verified' and evidence_links != ['verification.json']:
            raise ValueError('A verified feature requires verification.json evidence: ' + identifier)
        rows[identifier] = (implementation, verification, distribution,
                            tuple(evidence_links), tuple(link.replace('.ko.md', '.md') for link in specification_links))
    if not rows:
        raise ValueError('No feature status rows found')
    return rows


def external_inputs(root):
    """What the repository expects each external input to be, so a record can be wrong."""
    path = root / 'external-inputs.json'
    if not path.is_file():
        raise ValueError('A repository that records external inputs declares them in external-inputs.json')
    pin = json.loads(path.read_text(encoding='utf-8'))
    if pin.get('schema_version') != 1:
        raise ValueError('Unsupported external input pin schema')
    if not pin['pie'].get('release') or not re.fullmatch(r'[a-f0-9]{64}', pin['pie'].get('phar_sha256', '')):
        raise ValueError('The PIE pin requires a release and its content hash')
    supplementary = pin['supplementary']
    if (not re.fullmatch(r'[a-f0-9]{40}', supplementary.get('revision', ''))
            or not re.fullmatch(r'[a-f0-9]{64}', supplementary.get('inputs_sha256', ''))
            or type(supplementary.get('cases')) is not int or supplementary['cases'] <= 0):
        raise ValueError('The supplementary pin requires a revision, a content hash and a case count')
    return pin


def check_supplementary(record, counts, pin):
    """Supplementary inputs come from outside the repository, so they are pinned."""
    supplementary = record.get('supplementary')
    if not counts['supplementary']:
        if supplementary is not None:
            raise ValueError('Unused supplementary inputs cannot be recorded')
        return
    expected = {field: pin['supplementary'][field]
                for field in ('project', 'revision', 'cases', 'inputs_sha256')}
    if supplementary != expected or counts['supplementary'] != expected['cases']:
        raise ValueError('Supplementary inputs differ from the pin in external-inputs.json')


def check_verification(root, record):
    if record.get('schema_version') != 1 or record.get('status') != 'passed':
        raise ValueError('Verification record is not passed schema version 1')
    datetime.fromisoformat(record['checked_at'])
    if record.get('sources') != source_manifest(root):
        raise ValueError('Verification is stale: checked sources differ; run make check')
    counts = record['cases']
    if set(counts) != {'official', 'fixtures', 'supplementary', 'total'}:
        raise ValueError('Verification case counts are incomplete')
    if any(type(count) is not int or count < 0 for count in counts.values()):
        raise ValueError('Invalid verification case count')
    if counts['total'] != counts['official'] + counts['fixtures'] + counts['supplementary']:
        raise ValueError('Verification case total is inconsistent')
    official = json.loads((root / 'examples/official.json').read_text(encoding='utf-8'))
    fixtures = sum(len(list((root / 'fixtures' / category).glob('*.json'))) for category in ('valid', 'invalid'))
    if counts['official'] != len(official['cases']) or counts['fixtures'] != fixtures or not fixtures:
        raise ValueError('Verification counts do not match repository inputs')
    implementations = record['implementations']
    if set(implementations) != set(IMPLEMENTATIONS):
        raise ValueError('Verification requires all registered implementations')
    for name, result in implementations.items():
        if result.get('status') != 'passed' or result.get('cases') != counts['total'] or not result.get('runtime'):
            raise ValueError('Incomplete implementation result: ' + name)
        declared = REGISTRY['implementations'][name].get('tests') is not None
        recorded = (result.get('tests') or {}).get('status') == 'passed'
        if declared != recorded:
            raise ValueError('Package tests declared in the registry must be recorded as passed: ' + name)
    native = implementations.get('php-extension', {}).get('runtime', {})
    if 'php-extension' in implementations and (not native.get('extension_version') or not native.get('php')):
        raise ValueError('PHP runtime and extension versions must both be recorded')
    if record.get('packages', {}) != package_revisions(root):
        raise ValueError('Verification package records differ from the current source')
    tests = record['documentation_tests']
    if tests.get('status') != 'passed' or type(tests.get('count')) is not int or tests['count'] <= 0:
        raise ValueError('Passing documentation checker tests are required')
    check_supplementary(record, counts, external_inputs(root))


def check_distribution(record, features):
    if record.get('schema_version') != 1:
        raise ValueError('Invalid distribution schema')
    datetime.fromisoformat(record['checked_at'])
    source = record['source']
    if source.get('state') not in ('available', 'not-verified'):
        raise ValueError('Invalid source distribution state')
    if source.get('state') == 'available':
        if source.get('url') != 'https://github.com/polyspec/ordered-json' or source.get('branch') != 'main':
            raise ValueError('Confirmed source distribution is missing')
        if source.get('visibility') != 'public':
            raise ValueError('Source visibility observation is missing')
    if not isinstance(record.get('github_releases'), list) or not isinstance(record.get('version_tags'), list):
        raise ValueError('Release and tag observations are required')
    if 'implementation_sources' in record:
        observations = record['implementation_sources']
        if set(observations) != set(REGISTRY['repositories']):
            raise ValueError('Implementation source observations are incomplete')
        for name, observation in observations.items():
            expected_url = REGISTRY['repositories'][name]['url'].removesuffix('.git')
            if (observation.get('state') != 'available' or observation.get('url') != expected_url
                    or observation.get('branch') != 'main' or observation.get('visibility') != 'public'
                    or not re.fullmatch(r'[a-f0-9]{40}', observation.get('revision', ''))):
                raise ValueError('Invalid implementation source observation: ' + name)
            if not isinstance(observation.get('github_releases'), list) or not isinstance(observation.get('version_tags'), list):
                raise ValueError('Implementation release and tag observations are required: ' + name)
    registries = record['registries']
    if set(registries) != {'npm', 'crates.io', 'packagist', 'go', 'php-extension'}:
        raise ValueError('Registry observations are incomplete')
    published = set()
    for registry, observation in registries.items():
        if observation.get('state') == 'published':
            url = urlsplit(observation.get('artifact_url', ''))
            if url.scheme != 'https' or not url.netloc or not observation.get('version'):
                raise ValueError('A published artifact requires its version and URL: ' + registry)
            published.update(observation.get('features', []))
        elif observation.get('state') != 'not-verified':
            raise ValueError('Invalid registry observation: ' + registry)
    for identifier, (_, _, distribution, _, _) in features.items():
        if distribution == 'published' and identifier not in published:
            raise ValueError('Published feature has no observed artifact: ' + identifier)


def check_pie_verification(root, record):
    if record.get('schema_version') != 1 or record.get('scope') != 'pie-build' or record.get('status') != 'passed':
        raise ValueError('Invalid PIE verification record')
    datetime.fromisoformat(record['checked_at'])
    if record.get('sources') != source_manifest(root):
        raise ValueError('PIE verification is stale; run scripts/check_pie.py')
    if record.get('packages') != package_revisions(root):
        raise ValueError('PIE verification package records differ from the current source')
    if record.get('package') != 'ordered-json/ordered-json-extension:*@dev':
        raise ValueError('PIE verification uses an unexpected package')
    pin = external_inputs(root)
    if (record['pie'].get('phar_sha256') != pin['pie']['phar_sha256']
            or pin['pie']['release'] not in record['pie'].get('version', '')):
        raise ValueError('The PIE tool differs from the pin in external-inputs.json')
    declared = [path.relative_to(root).as_posix() for path in artifact_paths('php-extension', repository_paths(root))]
    if [record.get('artifact', {}).get('path')] != declared:
        raise ValueError('The record must name the artifact the registry declares')
    if set(record['artifact']) != {'path'}:
        raise ValueError('A linked module has no reproducible hash, so the record carries its path alone')
    commands = record['commands']
    if any(command.get('exit_code') != 0 for command in commands) or not any(
            command['arguments'][:1] == ['build'] for command in commands):
        raise ValueError('A successful PIE build is required')
    counts = record['cases']
    if set(counts) != {'official', 'fixtures', 'supplementary', 'total'} or any(
            type(value) is not int or value < 0 for value in counts.values()):
        raise ValueError('Invalid PIE verification case counts')
    if counts['total'] != counts['official'] + counts['fixtures'] + counts['supplementary']:
        raise ValueError('PIE verification case total is inconsistent')
    official = json.loads((root / 'examples/official.json').read_text())
    fixtures = sum(len(list((root / 'fixtures' / category).glob('*.json'))) for category in ('valid', 'invalid'))
    if counts['official'] != len(official['cases']) or counts['fixtures'] != fixtures:
        raise ValueError('PIE verification counts differ from the shared inputs')
    if set(record['implementations']) != {'php-extension'}:
        raise ValueError('PIE verification requires the native adapter')
    native = record['implementations']['php-extension']
    if native.get('status') != 'passed' or native.get('cases') != counts['total']:
        raise ValueError('The PIE artifact must pass every shared case')
    if not native['runtime'].get('php') or not native['runtime'].get('extension_version'):
        raise ValueError('PIE verification requires PHP and extension versions')
    check_supplementary(record, counts, pin)


def check_repository(root, include_children=True):
    root = root.resolve()
    errors, registered, identifiers, documents = [], set(), set(), {}

    def error(path, message):
        errors.append(f'{path}: {message}')

    def read_json(path):
        return json.loads((root / path).read_text(encoding='utf-8'))

    role = 'common'
    try:
        manifest = read_json('docs/documentation-manifest.json')
        if manifest.get('schema_version') != 1 or not isinstance(manifest.get('documents'), list):
            raise ValueError('Expected documentation manifest schema version 1')
        role = manifest.get('role', 'common')
        if role not in ('common', 'implementation', 'package'):
            raise ValueError('Unknown documentation repository role')
        for entry in manifest['documents']:
            identifier, en, ko, kind = (entry[key] for key in ('id', 'en', 'ko', 'kind'))
            if not re.fullmatch(r'[a-z][a-z0-9-]*', identifier) or identifier in identifiers:
                raise ValueError('Invalid or duplicate document ID: ' + identifier)
            identifiers.add(identifier)
            if kind not in KINDS or not en.endswith('.md') or en.endswith('.ko.md') or ko != en[:-3] + '.ko.md':
                raise ValueError('Invalid kind or translation path: ' + identifier)
            bodies, sections, blocks = [], [], []
            for name in (en, ko):
                if name in registered:
                    raise ValueError('Document is registered more than once: ' + name)
                registered.add(name)
                path = local_target(root, root / 'README.md', name)
                if path is None or not path.is_file():
                    raise ValueError('Document must be a repository file: ' + name)
                body = path.read_text(encoding='utf-8')
                if body.count(f'<!-- doc-id: {identifier} -->') != 1:
                    error(name, 'Missing or duplicate doc-id marker')
                if PRIVATE_PATH.search(body):
                    error(name, 'Public document contains a local home-directory path')
                prose, fenced = markdown_parts(body)
                anchors = ANCHOR.findall(prose)
                if len(anchors) != len(set(anchors)):
                    error(name, 'Duplicate section anchor')
                sections.append(anchors)
                blocks.append(fenced)
                bodies.append(body)
                documents[name] = prose
                for target in link_targets(prose):
                    try:
                        local_target(root, path, target)
                    except ValueError as issue:
                        error(name, str(issue))
            if sections[0] != sections[1]:
                error(ko, 'Section identifiers differ from English')
            if blocks[0] != blocks[1]:
                error(ko, 'Fenced code blocks differ from English')
            revisions = re.findall(r'<!-- source-sha256: ([a-f0-9]{64}) -->', bodies[1])
            if revisions != [sha256(bodies[0].encode('utf-8'))]:
                error(ko, 'Translation revision differs from English; review both documents')
    except (ValueError, KeyError, TypeError, OSError) as issue:
        error('docs/documentation-manifest.json', str(issue))

    for name in sorted(authored_markdown(root) - registered):
        error(name, 'Markdown document is not registered')

    features = {}
    if role == 'common':
        try:
            features = feature_rows(documents['docs/features.md'])
            if features != feature_rows(documents['docs/features.ko.md']):
                raise ValueError('English and Korean feature states or references differ')
            if any(row[1] != 'not-verified' for row in features.values()):
                check_verification(root, read_json('docs/verification.json'))
        except (ValueError, KeyError, TypeError, OSError) as issue:
            error('docs/features.md', str(issue))
        try:
            check_distribution(read_json('docs/distribution.json'), features)
        except (ValueError, KeyError, TypeError, OSError) as issue:
            error('docs/distribution.json', str(issue))
        if (root / 'docs/pie-verification.json').exists():
            try:
                check_pie_verification(root, read_json('docs/pie-verification.json'))
            except (ValueError, KeyError, TypeError, OSError) as issue:
                error('docs/pie-verification.json', str(issue))
        if include_children:
            for name, path in repository_paths(root).items():
                manifest = path / 'docs/documentation-manifest.json'
                if manifest.is_file():
                    child_errors, count, _ = check_repository(path, include_children=False)
                    errors.extend(name + '/' + issue for issue in child_errors)
    elif role == 'implementation':
        try:
            from standalone import validate_configuration
            validate_configuration(read_json('conformance.json'))
        except (ValueError, KeyError, TypeError, OSError) as issue:
            error('conformance.json', str(issue))

    for path in (root / 'docs').rglob('*.json'):
        try:
            body = path.read_text(encoding='utf-8')
            json.loads(body)
            if PRIVATE_PATH.search(body):
                error(path.relative_to(root), 'Public report contains a local home-directory path')
        except (ValueError, OSError) as issue:
            error(path.relative_to(root), str(issue))
    return errors, len(identifiers), len(features)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    errors, documents, features = check_repository(args.root)
    if errors:
        for issue in errors:
            print(issue, file=sys.stderr)
        return 1
    print(f'Documentation check passed: {documents} bilingual topics, {features} feature records.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

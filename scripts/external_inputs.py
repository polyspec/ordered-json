#!/usr/bin/env python3
"""Install the external inputs that external-inputs.json pins: the PIE PHAR and the supplementary JSON suite.

    python3 scripts/external_inputs.py     install both into .cache (make install-external)

Each input is an exact release or revision with its hash in external-inputs.json. The PHAR is downloaded from the PIE
release and refused unless its SHA-256 is the pinned one; the suite is fetched at its pinned revision and refused unless its
case count and inputs hash are the pinned ones. An input that is already installed with the pinned identity is not
downloaded again, and a refused input leaves nothing installed. These are the only downloads of this repository that scripts/kit
does not make: a check runs offline and names make install for a missing input."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PIE_FIX = 'run make install, which downloads the PIE release of external-inputs.json into .cache/pie/pie.phar'
SUITE_FIX = 'run make install, which installs the suite of external-inputs.json into .cache/JSONTestSuite'


def download(url):
    with urllib.request.urlopen(url, timeout=600) as response:
        return response.read()


PIE_PHAR = '.cache/pie/pie.phar'
PIE_DOWNLOAD = 'https://github.com/php/pie/releases/download/{release}/pie.phar'
SUITE = '.cache/JSONTestSuite'


def external_pins(root=ROOT):
    return json.loads((Path(root) / 'external-inputs.json').read_text(encoding='utf-8'))


def install_pie(root=ROOT, fetch=download):
    """Install the PIE PHAR that external-inputs.json pins into .cache/pie/pie.phar, the default PIE of make
    pie-check, unless that exact file is there."""
    pin = external_pins(root)['pie']
    target = Path(root) / PIE_PHAR
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == pin['phar_sha256']:
        print(f"PIE {pin['release']}: installed in {target}")
        return
    url = PIE_DOWNLOAD.format(release=pin['release'])
    data = fetch(url)
    actual = hashlib.sha256(data).hexdigest()
    if actual != pin['phar_sha256']:
        raise ValueError(f"PIE {pin['release']} {url}: expected sha256 {pin['phar_sha256']} (external-inputs.json), "
                         f'actual {actual}')
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.pie.phar.', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"PIE {pin['release']}: installed {url} into {target}")


def git_output(*arguments, cwd):
    return subprocess.run(['git', *arguments], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def suite_issues(pin, suite):
    """How the checkout `suite` differs from the supplementary pin, one message per field."""
    from verification_record import input_issues, supplementary_manifest  # It imports the registry.
    return input_issues({'supplementary': pin}, supplementary=supplementary_manifest(suite))


def install_suite(root=ROOT):
    """Install the supplementary suite that external-inputs.json pins into .cache/JSONTestSuite, the revision
    with its inputs hash, unless that revision with those inputs is there."""
    pin = external_pins(root)['supplementary']
    target = Path(root) / SUITE
    if (target / '.git').exists() and not suite_issues(pin, target):
        print(f"JSONTestSuite {pin['revision']}: installed in {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='JSONTestSuite-', dir=target.parent))
    retired = None
    try:
        git_output('init', '--quiet', cwd=staging)
        git_output('fetch', '--quiet', '--depth', '1', pin['url'], pin['revision'], cwd=staging)
        git_output('-c', 'advice.detachedHead=false', 'checkout', '--quiet', 'FETCH_HEAD', cwd=staging)
        issues = suite_issues(pin, staging)
        if issues:
            raise ValueError(f"JSONTestSuite {pin['url']} {pin['revision']} differs from external-inputs.json: "
                             + '; '.join(issues))
        if target.exists():
            retired = Path(tempfile.mkdtemp(prefix='JSONTestSuite-retired-', dir=target.parent))
            os.replace(target, retired / 'JSONTestSuite')
        os.replace(staging, target)
    finally:
        for leftover in (staging, retired):
            if leftover is not None and leftover.exists():
                shutil.rmtree(leftover)
    print(f"JSONTestSuite {pin['revision']}: installed {pin['url']} into {target}")


def main(argv):
    if argv:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        install_pie()
        install_suite()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'external inputs: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

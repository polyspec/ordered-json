"""The environment of every run: the tools are the declared releases, a check reads no network, and make install is the only
recipe that downloads.

The releases are declared in .node-version, the packageManager of package.json, rust-toolchain.toml, config/toolchain.json
and the pin files of the languages; scripts/kit/check-toolchain.mjs (make toolchain-check) compares the running tools with
them, and scripts/kit/check-cargo-downloads.mjs (make cargo-downloads-check) names make install for a missing crate. The
targets that run a tool depend on both checks, so no target works with a tool that no declaration names."""
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry import REGISTRY

ROOT = Path(__file__).resolve().parents[2]
OFFLINE = {'CARGO_NET_OFFLINE': 'true', 'GOPROXY': 'off', 'npm_config_offline': 'true', 'COMPOSER_DISABLE_NETWORK': '1'}
# The targets whose recipe starts cargo, go, PHP or a built adapter.
TOOL_TARGETS = ('verify-all', 'verify-js', 'verify-rust', 'verify-go', 'verify-php', 'verify-php-extension', 'verify-python',
                'clippy', 'go-vet', 'pie-check', 'benchmark', 'benchmark-check')


def makefile():
    return (ROOT / 'Makefile').read_text()


def recipes(text):
    """{target: [recipe lines]} of the targets of a Makefile."""
    found, target = {}, None
    for line in text.splitlines():
        header = re.match(r'^([A-Za-z0-9_.-]+(?: [A-Za-z0-9_.-]+)*):(?!=)(.*)$', line)
        if header and not line.startswith('\t'):
            target = header.group(1)
            found.setdefault(target, [])
            found[target].append(('prerequisites', header.group(2).split('#')[0].split()))
        elif line.startswith('\t') and target:
            found[target].append(('recipe', line.strip()))
        elif line.strip() and not line.startswith('#'):
            target = None
    return found


class Environment(unittest.TestCase):
    def test_no_command_installs_or_selects_another_toolchain(self):
        text = makefile()
        self.assertRegex(text, r'(?m)^export GOTOOLCHAIN := local$')
        self.assertRegex(text, r'(?m)^export RUSTUP_AUTO_INSTALL := 0$')
        self.assertEqual(REGISTRY['implementations']['go']['env'].get('GOTOOLCHAIN'), 'local')
        self.assertEqual(REGISTRY['implementations']['rust']['env'].get('RUSTUP_AUTO_INSTALL'), '0')

    def test_every_check_runs_offline_and_only_make_install_downloads(self):
        # A check reads no network: make install downloads what the checks read, and cargo, go, npm and Composer run
        # offline in every other command, so a missing download fails at once instead of reaching a registry.
        text = makefile()
        for name, value in OFFLINE.items():
            with self.subTest(variable=name):
                self.assertRegex(text, rf'(?m)^export {name} := {value}$')
        self.assertRegex(text, r'(?m)^ONLINE := env' + ''.join(rf' -u {name}' for name in OFFLINE) + '$')
        downloading = sorted(target for target, lines in recipes(text).items()
                             if any(kind == 'recipe' and '$(ONLINE)' in line for kind, line in lines))
        self.assertEqual(downloading, ['install-external', 'install-rust'])

    def test_make_install_makes_every_download_of_the_checks(self):
        # The npm, Go and Composer releases of config/toolchain.json and package.json, the Rust toolchain, the crates of
        # rust/Cargo.lock, the PIE PHAR and the supplementary suite.
        prerequisites = [item for kind, items in recipes(makefile())['install'] if kind == 'prerequisites' for item in items]
        self.assertEqual(prerequisites, ['install-tools', 'install-rust', 'cargo-downloads-fetch', 'install-external'])
        downloads = dict(recipes(makefile()))
        self.assertEqual([line for kind, line in downloads['install-external'] if kind == 'recipe'],
                         ['$(ONLINE) $(PYTHON) scripts/external_inputs.py'])
        self.assertEqual([line for kind, line in downloads['install-rust'] if kind == 'recipe'],
                         ['$(ONLINE) rustup toolchain install --no-self-update'])

    def test_a_target_that_runs_a_tool_depends_on_the_toolchain_and_download_checks(self):
        table = recipes(makefile())
        for target in TOOL_TARGETS:
            prerequisites = [item for kind, items in table[target] if kind == 'prerequisites' for item in items]
            with self.subTest(target=target):
                self.assertIn('toolchain-check', prerequisites)
                self.assertIn('cargo-downloads-check', prerequisites)

    def test_the_checkout_tools_come_first_on_the_path(self):
        self.assertRegex(makefile(), r'(?m)^export PATH := \$\(CURDIR\)/var/tools/bin:')

    def test_the_declarations_name_an_exact_release_or_a_minor_release(self):
        self.assertRegex((ROOT / '.node-version').read_text(), r'\A\d+\.\d+\.\d+\n\Z')
        self.assertRegex((ROOT / '.python-version').read_text(), r'\A\d+\.\d+\n\Z')
        self.assertRegex((ROOT / '.php-version').read_text(), r'\A\d+\.\d+\n\Z')
        self.assertRegex((ROOT / 'rust-toolchain.toml').read_text(), r'(?m)^channel = "\d+\.\d+\.\d+"$')
        manager = json.loads((ROOT / 'package.json').read_text())['packageManager']
        self.assertRegex(manager, r'^npm@\d+\.\d+\.\d+\+sha512\.[0-9a-f]{128}$')
        self.assertRegex((ROOT / 'go/go.mod').read_text(), r'(?m)^toolchain go\d+\.\d+\.\d+$')

    def test_no_recipe_runs_a_pinned_tool_by_name(self):
        # The tools of scripts/kit are started with node, whose release .node-version pins and make toolchain-check compares;
        # every other tool starts from a script that sets the PATH of the run (GNU Make 3.81 looks a simple recipe command up
        # on its own PATH, not the exported one).
        lines = [line.strip() for line in makefile().splitlines() if line.startswith('\t')]
        self.assertTrue(lines)
        for line in lines:
            command = re.sub(r'^[@\-]*(\$\(ONLINE\) )?', '', line)
            with self.subTest(recipe=line):
                self.assertNotRegex(re.sub(r'--only \S+', '', command), r'(^|[\s;&|(])(npm|npx|go|cargo|rustc)(\s|$)')
                self.assertNotRegex(command, r'^node (?!scripts/kit/|-p )')

    def test_every_cargo_command_uses_the_lock_file(self):
        implementation = REGISTRY['implementations']['rust']
        commands = [step['command'] for step in implementation['prepare']]
        commands += [implementation[key]['command'] for key in ('tests', 'test_cases', 'api_symbols')]
        for command in commands:
            if command[0] == '{cargo}' and command[1] != 'fmt':
                with self.subTest(command=command):
                    self.assertIn('--locked', command)
        self.assertIn('"--locked"', (ROOT / 'benchmarks/run.py').read_text().split('"cargo", "run"', 1)[1].split(']')[0])


if __name__ == '__main__':
    unittest.main()

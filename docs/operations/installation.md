<!-- doc-id: installation -->
# Installation and execution

[한국어](installation.ko.md)

<a id="requirements"></a>
## Requirements and identifiers

| Component | Declared requirement | Current identifier | Metadata |
| --- | --- | --- | --- |
| JavaScript | Node.js >= 20, ESM | `@polyspec/ordered-json`, 0.0.2 | [package.json](https://github.com/polyspec/ordered-json/blob/main/js/package.json) |
| Rust | Rust >= 1.71, edition 2021 | `polyspec-ordered-json`, 0.0.2 | [Cargo.toml](https://github.com/polyspec/ordered-json/blob/main/rust/Cargo.toml) |
| Go | Go >= 1.22 | `github.com/polyspec/ordered-json/go` module, `orderedjson` package | [go.mod](https://github.com/polyspec/ordered-json/blob/main/go/go.mod) |
| PHP | PHP >= 8.2, JSON and PCRE extensions | `polyspec/ordered-json`, `Polyspec\OrderedJson` namespace | [composer.json](https://github.com/polyspec/ordered-json/blob/main/php/composer.json) |
| Native PHP | Matching PHP development headers, C compiler, phpize, make | `ordered_json` extension, 0.0.2 | [extension source](https://github.com/polyspec/ordered-json/blob/main/php-extension/src/ordered_json.c) |
| Repository checks | The pinned Python, Node.js, Rust, Go and npm releases, Git, make, PHP above | `make tools`, `make check` | [verification](validation.md) |

The repository checks run with the exact releases that tracked files pin: Node.js in `.node-version`, Rust in `rust-toolchain.toml`, Go in the `toolchain` line of `go/go.mod`, Python by its minor release in `.python-version`, PHP by its minor release in `.php-version`, and npm with the SHA-512 of its registry tarball in the `packageManager` field of `package.json`. `make tools` installs that Rust toolchain with rustup and that npm into `.cache/tools/npm` of the checkout, which Git ignores; no npm of the machine is used or changed. `make toolchains-check` compares every tool with its pin, and each entry point of the checks does the same before its first step and fails with the expected and the actual version, or the error of the command, of each tool that differs. `GOTOOLCHAIN=local` and `RUSTUP_AUTO_INSTALL=0` keep go and rustup from downloading or installing another toolchain during a run, and every cargo command uses `--locked`.

The table lists declared minimum versions, not a claim that every minimum version was tested. Actual versions are recorded in the [records](validation.md#records) of the run that verifies a commit. JavaScript, Rust, and Go have no external runtime library dependencies.

<a id="checkout"></a>
## Source checkout

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
~~~

The clone contains every implementation package. Use the package directory or a published package when available. Registry installation and publication are not verified; see [distribution](distribution.md).

- JavaScript: import from `js/index.js`. TypeScript declarations are in `js/index.d.ts`.
- Rust: set a local Cargo dependency with `path` pointing to `rust/`.
- Go: use a local `replace` for module `github.com/polyspec/ordered-json/go` pointing to `go/`.
- PHP: require `php/src/OrderedJson.php` or use `php/` as a Composer path repository.

<a id="release-assets"></a>
## Release assets

Each GitHub Release `vX.Y.Z` carries `polyspec-ordered-json-X.Y.Z.tgz`, `polyspec-ordered-json-X.Y.Z.zip` and `polyspec-ordered-json-extension-X.Y.Z.zip`. Each archive carries the manifest of its package unchanged: `package.json` of `js/` and `composer.json` of `php/` and `php-extension/`, each with `version` X.Y.Z, without `repositories` and without `@dev`.

npm installs the tarball by its path:

~~~sh
mkdir app && cd app
npm init -y
npm install ./polyspec-ordered-json-X.Y.Z.tgz
~~~

Composer installs the zips from an artifact repository, a directory that holds them. With the zips in `assets/` next to `composer.json`:

~~~json
{
  "repositories": [
    {"type": "artifact", "url": "assets"},
    {"packagist.org": false}
  ],
  "require": {"polyspec/ordered-json": "X.Y.Z"}
}
~~~

~~~sh
composer install
~~~

Composer reads both zips. It does not install `polyspec/ordered-json-extension`, a package of the type `php-ext`; PIE builds and installs it ([native PHP](#native-php)).

The packages of this repository depend on no other package, so the repository has no npm workspaces and no private development manifest: the root `package.json` and `composer.json` declare the same packages as `js/` and `php/` for an install from a checkout, with the same `version` and no `repositories`. `scripts/tests/test_release.py` builds the archives and installs them in a temporary project outside the repository: npm with an empty cache and the scope `@polyspec` pointed at an unreachable registry, and Composer with an empty `COMPOSER_HOME` and `COMPOSER_CACHE_DIR` and the artifact repository of the zips.

<a id="native-php"></a>
## Native PHP

Build against the PHP runtime that will load the extension:

~~~sh
cd php-extension/src
if test -f Makefile; then make distclean; fi
phpize --clean
phpize
./configure --enable-ordered-json
make -j2
~~~

The current Unix build produces `php-extension/src/modules/ordered_json.so`. From the repository root:

~~~sh
php -n -d extension="$PWD/php-extension/src/modules/ordered_json.so" script.php
~~~

`script.php` is any PHP script that uses the extension. `php -n` ignores php.ini; required built-in JSON and PCRE support must still be available. The source includes `config.w32`, but Windows and ZTS builds have not been verified. PIE requires its build tools, including `pkg-config`; on macOS the Homebrew package is `pkgconf`. See the [PIE artifact check](validation.md#pie) for the reproducible PIE build and shared verification procedure.

On macOS, configure preserves an explicit `MACOSX_DEPLOYMENT_TARGET` or derives the missing value from the active C compiler, including target flags in `CFLAGS`. The loadable bundle uses dynamic symbol lookup for modern targets and omits the unused dynamic-library single-module flag check.

The common PHP API and backend selection rules are defined in the [API contract](../spec/api.md#php). Rebuild the module after native source or PHP build configuration changes.

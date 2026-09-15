<!-- doc-id: installation -->
# Installation and execution

[한국어](installation.ko.md)

<a id="requirements"></a>
## Requirements and identifiers

| Component | Declared requirement | Current identifier | Metadata |
| --- | --- | --- | --- |
| JavaScript | Node.js >= 20, ESM | `ordered-json`, 0.0.1 | [package.json](https://github.com/polyspec/ordered-json/blob/main/js/package.json) |
| Rust | Rust >= 1.70, edition 2021 | `ordered-json`, 0.0.1 | [Cargo.toml](https://github.com/polyspec/ordered-json/blob/main/rust/Cargo.toml) |
| Go | Go >= 1.22 | `github.com/polyspec/ordered-json/go` module, `orderedjson` package | [go.mod](https://github.com/polyspec/ordered-json/blob/main/go/go.mod) |
| PHP | PHP >= 8.2, JSON and PCRE extensions | `ordered-json/ordered-json`, `OrderedJson` namespace | [composer.json](https://github.com/polyspec/ordered-json/blob/main/php/composer.json) |
| Native PHP | Matching PHP development headers, C compiler, phpize, make | `ordered_json` extension, 0.0.1 | [extension source](https://github.com/polyspec/ordered-json/blob/main/php-extension/src/ordered_json.c) |
| Repository checks | Python >= 3.9, Git, make, all runtimes above | `make check` | [verification](validation.md) |

These are declared minimum versions, not a claim that every minimum version was tested. Actual versions are recorded in [verification.json](../verification.json). JavaScript, Rust, and Go have no external runtime library dependencies.

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
php -n -d extension="$PWD/php-extension/src/modules/ordered_json.so" application.php
~~~

`application.php` is the caller's application. `php -n` ignores php.ini; required built-in JSON and PCRE support must still be available. The source includes `config.w32`, but Windows and ZTS builds have not been verified. PIE requires its build tools, including `pkg-config`; on macOS the Homebrew package is `pkgconf`. See the [PIE artifact check](validation.md#pie) for the reproducible PIE build and shared verification procedure.

On macOS, configure preserves an explicit `MACOSX_DEPLOYMENT_TARGET` or derives the missing value from the active C compiler, including target flags in `CFLAGS`. The loadable bundle uses dynamic symbol lookup for modern targets and omits the unused dynamic-library single-module flag check.

The common PHP API and backend selection rules are defined in the [API contract](../spec/api.md#php). Rebuild the module after native source or PHP build configuration changes.

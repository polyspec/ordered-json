<!-- doc-id: installation -->
# Installation and execution

[한국어](installation.ko.md)

<a id="requirements"></a>
## Requirements and identifiers

| Component | Declared requirement | Current identifier | Metadata |
| --- | --- | --- | --- |
| JavaScript | Node.js >= 20, ESM | `ordered-json`, 0.1.0 | [package.json](../../js/package.json) |
| Rust | Rust >= 1.70, edition 2021 | `ordered-json`, 0.1.0 | [Cargo.toml](../../rust/Cargo.toml) |
| Go | Go >= 1.22 | `github.com/ordered-json/ordered-json/go` module, `orderedjson` package | [go.mod](../../go/go.mod) |
| PHP | PHP >= 8.2, JSON and PCRE extensions | `ordered-json/ordered-json`, `OrderedJson` namespace | [composer.json](../../php/composer.json) |
| Native PHP | Matching PHP development headers, C compiler, phpize, make | `ordered_json` extension, 0.1.0 | [extension source](../../php/ext/ordered_json.c) |
| Repository checks | Python >= 3.9, Git, make, all runtimes above | `make check` | [verification](validation.md) |

These are declared minimum versions, not a claim that every minimum version was tested. Actual versions are recorded in [verification.json](../verification.json). JavaScript, Rust, and Go have no external runtime library dependencies.

<a id="checkout"></a>
## Source checkout

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
~~~

Use the local module or source directory. Registry installation and publication are not verified; see [distribution](distribution.md).

- JavaScript: import from `js/index.js`. TypeScript declarations are in `js/index.d.ts`.
- Rust: set a local Cargo dependency with `path` pointing to `rust/`.
- Go: use a local `replace` for module `github.com/ordered-json/ordered-json/go` pointing to `go/`.
- PHP: require `php/src/OrderedJson.php` or use `php/` as a Composer path repository.

<a id="native-php"></a>
## Native PHP

Build against the PHP runtime that will load the extension:

~~~sh
cd php/ext
phpize --clean
phpize
./configure --enable-ordered-json
make -j2
~~~

The current Unix build produces `php/ext/modules/ordered_json.so`. From the repository root:

~~~sh
php -n -d extension="$PWD/php/ext/modules/ordered_json.so" script.php
~~~

`script.php` is any PHP script that uses the extension. `php -n` ignores php.ini; required built-in JSON and PCRE support must still be available. The source includes `config.w32`, but a Windows build has not been verified.

The common PHP API and backend selection rules are defined in the [API contract](../spec/api.md#php). Rebuild the module after native source or PHP build configuration changes.

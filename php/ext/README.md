<!-- doc-id: php-extension -->
# PHP extension

[한국어](README.ko.md)

<a id="usage"></a>
## Build and use

The C extension implements strict parsing and associative JSON serialization. The [common PHP package](../README.md) provides the public API. The extension's `ordered_json` version and the PHP runtime version are separate; both are recorded in [verification.json](../../docs/verification.json).

Follow [native installation](../../docs/operations/installation.md#native-php) to build `modules/ordered_json.so` for the target PHP runtime. The [API contract](../../docs/spec/api.md#php) defines `ordered_json_scan`, `ordered_json_compact`, descriptor fields, and parser selection. Windows configuration is included, but a Windows build has not been verified.

<a id="verification"></a>
## Verification

After building, run from the repository root:

~~~sh
python3 scripts/verify.py --only php-native
~~~

The adapter requires the extension and uses the shared official expectations. The [repository check](../../docs/operations/validation.md) builds the extension and compares both PHP backends with the other implementations.

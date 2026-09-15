<!-- doc-id: repositories -->
# Repository contract

[한국어](repositories.ko.md)

<a id="ownership"></a>
## Ownership

The repository owns the JSON specification, official inputs and expected results, shared verifier, implementation registry, aggregate verification records, and all implementation source. Each language directory owns its source, adapter, package metadata, documentation, and package build configuration within the same Git revision.

| Package | Checkout path | Implementation |
| --- | --- | --- |
| common | . | Contract, fixtures, verification and registry |
| javascript | js | JavaScript |
| rust | rust | Rust |
| go | go | Go |
| php | php | Pure PHP and the PHP Value API |
| php-extension | php-extension | Native PHP extension |

The repository records one revision for the common contract and all implementations. The implementation directories do not contain nested Git repositories or reverse submodules. Pure PHP and the extension retain separate package metadata and build processes, but their source changes are reviewed and verified in the same repository revision. The native implementation is tested against the PHP Value API in that same revision.

<a id="verification"></a>
## Shared verification

Official inputs and expected results exist only in the common repository. Adapters return the shared reporting protocol and contain no independent goldens. The implementation registry declares repository locations, adapter commands, build commands, and runtime version commands. Adding a language must not require changing the JSON comparison algorithm.

Each package check runs against the verifier and fixtures in the same checkout. Test reports identify the common revision, implementation paths, dependencies, runtimes, and results. The aggregate check verifies every registered implementation from the same working tree and rejects an incomplete package or missing declared build command.

<a id="documents"></a>
## Documents and changes

Each repository registers its own English documents and Korean translations. Shared contracts and aggregate feature state are referenced from implementation documents. The common documentation check also checks documents in initialized implementation repositories.

For a shared contract change, update the verifier, affected implementations, and conformance fixtures in one change, run package and aggregate checks, then publish the resulting repository revision. Test success and source or package publication remain separate observations.

<a id="php-extension"></a>
## PHP extension package

The PHP library uses Composer package `ordered-json/ordered-json`. The extension uses the distinct PIE package `ordered-json/ordered-json-extension`, type `php-ext`, extension name `ordered_json`, and build path `src`. Its configuration enables a standalone extension build by default. The PHP library is a test dependency, not a native build or PIE package dependency.

On macOS, configure preserves an explicit `MACOSX_DEPLOYMENT_TARGET` or obtains the missing value from the active C compiler's deployment target. The extension is a loadable bundle; configure uses Libtool's `LT_MULTI_MODULE` option to omit the unnecessary dynamic-library single-module flag check. Modern macOS targets use dynamic symbol lookup. Ordinary and PIE builds must complete without the obsolete `-single_module` and `-undefined suppress` warnings.

PIE package recognition, a local PIE build, and the shared JSON check against the PIE-built artifact must succeed before recording PIE compatibility. A local build does not establish Packagist publication, a released version, Windows binary availability, or installation into a user's PHP configuration. The [PIE maintainer contract](https://github.com/php/pie/blob/1.4.10/docs/extension-maintainers.md) defines package metadata and build behavior.

<a id="state"></a>
## Implementation state

The five implementation packages are maintained in this repository. [Feature state](../features.md) records completion and evidence separately from this contract.

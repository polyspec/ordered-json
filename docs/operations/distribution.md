<!-- doc-id: distribution -->
# Distribution

[한국어](distribution.ko.md)

<a id="state"></a>
## Observed state

[distribution.json](../distribution.json) records source and publication observations. The repository holds the five [implementation packages](../spec/repositories.md#ownership) in one revision. No GitHub releases or version tags were found in the recorded observations.

Registry publication for npm, crates.io, Packagist, Go, and the PHP extension is not verified. Source checkout is the confirmed local distribution. PIE metadata and a passing PIE build establish local build compatibility, not Packagist publication. The extension package is `polyspec/ordered-json-extension`; the PHP library is `polyspec/ordered-json`.

Source version strings do not establish a released artifact. Registry publishing workflows are not configured; hosted CI runs the full suite and the push gate ([hosted CI](validation.md#ci)), and the push of a tag creates the GitHub Release of the tag ([tag releases](#tag-release)). LICENSE files are not present.

<a id="source-publication"></a>
## Source publication

Run each changed package's required checks and commit the package with the common contract. Every change reaches `main` through a pull request and the merge queue ([publishing main](validation.md#publish)):

~~~sh
git push origin HEAD:refs/heads/<branch>
gh pr create --base main --head <branch> --fill
gh pr merge <branch> --auto --rebase
~~~

Hosted CI runs the aggregate and PIE checks on the pull request and on the merge group, and the merge queue moves `main` to the commit whose required checks passed. Verify a clean clone can build every package from the published revision. A shared contract change is published only with its verifier, fixtures, and affected packages in that same revision.

Keep authentication information in the system credential store. Keep publication observations separate from test results.

<a id="tag-release"></a>
## Tag releases

A release is a tag of a commit of `main` ([release procedure](../../AGENTS.md#release)): `vX.Y.Z` releases the npm package of `js/` and the Composer packages of `php/` and `php-extension/` at version X.Y.Z, and `go/vX.Y.Z` releases the Go module `github.com/polyspec/ordered-json/go`. The Cargo package of `rust/` is not released as an archive; it is consumed by git tag, because `cargo package` rewrites git dependencies into crates.io requirements that do not resolve. The push of the tag runs `.github/workflows/release.yml` (`on: push: tags: ['v*', '**/v*']`, permission `contents: write`; in a tag filter `*` does not match `/`, so `**/v*` covers the tag of a Go module at any depth), whose steps run `scripts/release.py` in this order and stop at the first failure:

~~~sh
make release-verify
make release-versions
make release-assets
make release-publish
~~~

1. `make release-verify` requires the tagged commit to be an ancestor of `origin/main` (`git merge-base --is-ancestor`) and the latest check runs `push-gate` and `ci-passed` of that commit (`gh api repos/<repository>/commits/<sha>/check-runs`) to be completed with the conclusion `success`; it names a missing or failed check and does not run the tests again.
2. `make release-versions` requires X.Y.Z in every manifest: `package.json`, `js/package.json`, `composer.json`, `php/composer.json`, `php-extension/composer.json` and `rust/Cargo.toml` (a `composer.json` declares `version`, because a Composer artifact repository reads the version of the manifest) and the section `## X.Y.Z` in `CHANGELOG.md`, and names each file with its version and the version of the tag; for `go/vX.Y.Z` it requires the module path of `go/go.mod` and the section.
3. `make release-assets` builds `var/release/assets`: `polyspec-ordered-json-X.Y.Z.tgz` (`npm pack` of `js/`), `polyspec-ordered-json-X.Y.Z.zip` and `polyspec-ordered-json-extension-X.Y.Z.zip` (`git archive` of `php/` and `php-extension/` of the tagged commit): the release assets are npm tarballs and Composer zips only. An archive is named `<package name>-<version>.<ext>`, with `@scope/` and `vendor/` written as `scope-` and `vendor-`. Before it packs, every published manifest of the tagged commit must be in the standard form: a `composer.json` declares `version` and no `repositories`, no constraint holds `@dev`, a `package.json` declares no `overrides` and no `file:`, `link:`, `workspace:`, URL or git dependency, and a dependency on a polyspec package is one exact version. A zip has stored entries, the entry time 1985-10-26T08:15:00Z that npm pack also uses, and is written with `TZ=UTC`, so the zip of a tree has the same bytes on every machine and at every time and a consumer lock pins it by its shasum. After it packs, the manifest of each archive must equal the manifest of the tagged commit byte for byte; no step rewrites a manifest. `scripts/tests/test_release.py` requires the same standard form of the tree in `make check`. A Go tag builds and attaches nothing.
4. `make release-publish` runs `gh release create <tag> --verify-tag --title <tag> --notes-file <notes>` with the archives. GitHub refuses a release body over 125000 characters, so the notes are the section `## X.Y.Z` of `CHANGELOG.md` when it has at most 125000 characters, and otherwise the one line `The changes of X.Y.Z are listed in [CHANGELOG.md](https://github.com/polyspec/ordered-json/blob/<tag>/CHANGELOG.md#<anchor>).`, with the tag URL-encoded per path segment and the `<a id>` anchor of the section, or the version without its dots when the section has none.

The tag reaches the steps through the environment variable `TAG`. `scripts/tests/test_release.py` runs each step against fakes of `gh` and `npm`, and `scripts/tests/test_workflow_rules.py` requires the trigger, the permission and the order of the steps.

<a id="releases"></a>
## Registry and release records

No registry publication is established or verified. Before recording a release, verify its package name, version, included files, registry, artifact, and tested source revision. Record the artifact URL and publication observation separately. Register the extension for PIE through Packagist using its `php-ext` Composer metadata when publishing a release.

Update English and Korean distribution documents, feature distribution state, and the changelog when publication state changes. Do not infer publication from a test, version declaration, planned tag, or source push.

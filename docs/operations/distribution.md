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

A release is a tag of a commit of `main` ([release procedure](../../AGENTS.md#release)): `vX.Y.Z` releases the npm package of `js/`, the Composer packages of `php/` and `php-extension/` and the Cargo package of `rust/` at version X.Y.Z, and `go/vX.Y.Z` releases the Go module `github.com/polyspec/ordered-json/go`. The push of the tag runs `.github/workflows/release.yml` (`on: push: tags: ['v*', '*/v*']`, permission `contents: write`), whose steps run `scripts/release.py` in this order and stop at the first failure:

~~~sh
make release-verify
make release-versions
make release-assets
make release-publish
~~~

1. `make release-verify` requires the tagged commit to be an ancestor of `origin/main` (`git merge-base --is-ancestor`) and the latest check runs `push-gate` and `ci-passed` of that commit (`gh api repos/<repository>/commits/<sha>/check-runs`) to be completed with the conclusion `success`; it names a missing or failed check and does not run the tests again.
2. `make release-versions` requires X.Y.Z in `package.json`, `js/package.json` and `rust/Cargo.toml` (a `composer.json` without a `version` field takes the version from the tag, as Composer does) and the section `## X.Y.Z` in `CHANGELOG.md`, and names each file with its version and the version of the tag; for `go/vX.Y.Z` it requires the module path of `go/go.mod` and the section.
3. `make release-assets` builds `var/release/assets`: `polyspec-ordered-json-X.Y.Z.tgz` (`npm pack` of `js/`), `polyspec-ordered-json-X.Y.Z.zip` and `polyspec-ordered-json-extension-X.Y.Z.zip` (`git archive` of `php/` and `php-extension/` of the tagged commit) and `polyspec-ordered-json-X.Y.Z.crate` (`cargo package --no-verify --locked` of `rust/`). An archive is named `<package name>-<version>.<ext>`, with `@scope/` and `vendor/` written as `scope-` and `vendor-`. A Go tag builds none.
4. `make release-publish` runs `gh release create <tag> --verify-tag --title <tag> --notes-file <the section X.Y.Z>` with the archives.

The tag reaches the steps through the environment variable `TAG`. `scripts/tests/test_release.py` runs each step against fakes of `gh`, `npm` and `cargo`, and `scripts/tests/test_workflow_rules.py` requires the trigger, the permission and the order of the steps.

<a id="releases"></a>
## Registry and release records

No registry publication is established or verified. Before recording a release, verify its package name, version, included files, registry, artifact, and tested source revision. Record the artifact URL and publication observation separately. Register the extension for PIE through Packagist using its `php-ext` Composer metadata when publishing a release.

Update English and Korean distribution documents, feature distribution state, and the changelog when publication state changes. Do not infer publication from a test, version declaration, planned tag, or source push.

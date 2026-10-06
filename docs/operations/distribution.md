<!-- doc-id: distribution -->
# Distribution

[한국어](distribution.ko.md)

<a id="state"></a>
## Observed state

[distribution.json](../distribution.json) records source and publication observations. The repository holds the five [implementation packages](../spec/repositories.md#ownership) in one revision. No GitHub releases or version tags were found in the recorded observations.

Registry publication for npm, crates.io, Packagist, Go, and the PHP extension is not verified. Source checkout is the confirmed local distribution. PIE metadata and a passing PIE build establish local build compatibility, not Packagist publication. The extension package is `polyspec/ordered-json-extension`; the PHP library is `polyspec/ordered-json`.

Source version strings do not establish a released artifact. Registry publishing workflows are not configured; hosted CI runs the full suite and the push gate ([hosted CI](validation.md#ci)). LICENSE files are not present.

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

<a id="releases"></a>
## Registry and release records

No registry publication is established or verified. Before recording a release, verify its package name, version, included files, registry, artifact, and tested source revision. Record the artifact URL and publication observation separately. Register the extension for PIE through Packagist using its `php-ext` Composer metadata when publishing a release.

Update English and Korean distribution documents, feature distribution state, and the changelog when publication state changes. Do not infer publication from a test, version declaration, planned tag, or source push.

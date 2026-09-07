<!-- doc-id: distribution -->
# Distribution

[한국어](distribution.ko.md)

<a id="state"></a>
## Observed state

The canonical publication observations are in [distribution.json](../distribution.json). Source is available in the public [ordered-json repository](https://github.com/polyspec/ordered-json), on `main`. The recorded observation contains no GitHub releases or version tags.

Registry publication for npm, crates.io, Packagist, Go, and the PHP extension is not verified. The confirmed distribution is source checkout. Version strings in source metadata do not establish a released artifact. There is no registry publishing workflow or hosted CI configuration in this repository. A LICENSE file is not present.

<a id="source-publication"></a>
## Source publication

After the required checks succeed, publish authorized source changes:

~~~sh
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
~~~

Compare the full local and remote commit IDs. Record a source publication only when they match. Authentication details belong in the system credential store, not repository documents.

<a id="releases"></a>
## Registry and release records

No registry publishing command is established or verified for this repository. Before recording a release, verify the exact package name, version, included files, target registry, published artifact, and its relationship to the tested source. Record the artifact URL and the observation separately from verification results.

Update the English and Korean distribution documents, feature distribution state, and changelog when publication state changes. Do not infer publication from a successful test, version declaration, tag plan, or push of source files.

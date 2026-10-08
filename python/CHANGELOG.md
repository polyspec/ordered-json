<!-- doc-id: python-changelog -->
# Changelog

[한국어](CHANGELOG.ko.md)

<a id="unreleased"></a>
## Unreleased

- The package implements the shared JSON contract (T1.27-2): `parse` and `parse_bytes` read text and UTF-8 bytes,
  `stringify` and `Value.compact()` serialize, `Value` exposes the accessors and factories, and `ParseError` reports
  the shared rejection kinds at UTF-8 byte offsets, with `max_depth` and `reject_duplicates` following the JavaScript
  binding. The package tests run the standard cases and its own cases, and the registry, the package test standard
  and the owner map of the repository cover the package.

<!-- doc-id: python-changelog -->
<!-- source-sha256: 8cab3bd11f254a9f7f1eef39abc22f3581c45bc15b0c5683150b1f1f0b385c48 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## Unreleased

- `parse_bytes`는 Python으로 byte마다 검사하지 않고 `bytes.decode('utf-8')`로 UTF-8을 검증합니다 (T1.35). 거부는 이전과 같은 offset인
  `UnicodeDecodeError`의 `start`에서의 `invalid_utf8`이며, `ParseError`는 그 error에서 발생합니다.

- 패키지가 공유 JSON 계약을 구현합니다 (T1.27-2). `parse`와 `parse_bytes`가 text와 UTF-8 byte를 읽고,
  `stringify`와 `Value.compact()`가 직렬화하며, `Value`가 접근자와 factory를 노출하고, `ParseError`가 공유
  rejection kind를 UTF-8 byte offset으로 보고합니다. `max_depth`와 `reject_duplicates`는 JavaScript binding을
  따릅니다. 패키지 test가 표준 사례와 자기 사례를 실행하고, 저장소의 registry, 패키지 test 표준, owner map이
  패키지를 다룹니다.

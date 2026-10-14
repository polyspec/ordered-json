<!-- doc-id: python-changelog -->
<!-- source-sha256: 9c6b9c6e0892062203d8eb58aa14adf825124a578921373009dfb92e6309816f -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## Unreleased

- parser는 문서를 compiled `re` pattern의 한 pass로, member, item, root 값마다 match 하나로 읽고, member 이름과
  `string_value()`를 `bytes.decode`와 `json.decoder.scanstring`으로 decode합니다 (T1.41). 평평한 객체 50,000개에서 CPU
  시간은 순수 PHP parser의 4.44배에서 2.34-2.94배로 내려갔으며, 결과와 오류 offset은 같습니다.

- `parse_bytes`는 Python으로 byte마다 검사하지 않고 `bytes.decode('utf-8')`로 UTF-8을 검증합니다 (T1.35). 거부는 이전과 같은 offset인
  `UnicodeDecodeError`의 `start`에서의 `invalid_utf8`이며, `ParseError`는 그 error에서 발생합니다.

- 패키지가 공유 JSON 계약을 구현합니다 (T1.27-2). `parse`와 `parse_bytes`가 text와 UTF-8 byte를 읽고,
  `stringify`와 `Value.compact()`가 직렬화하며, `Value`가 접근자와 factory를 노출하고, `ParseError`가 공유
  rejection kind를 UTF-8 byte offset으로 보고합니다. `max_depth`와 `reject_duplicates`는 JavaScript binding을
  따릅니다. 패키지 test가 표준 사례와 자기 사례를 실행하고, 저장소의 registry, 패키지 test 표준, owner map이
  패키지를 다룹니다.

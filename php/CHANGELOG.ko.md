<!-- doc-id: changelog -->
<!-- source-sha256: fed796c1211d2b7bec21824515e75b19e12efc12132f61381c51224aec3ef57d -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- `useNative` 파싱 옵션, `parseNative()`, 사용하지 않는 `stringify()` compact 인자를 제거했습니다. `parse()`는 확장이 로드돼 있으면 확장을 사용합니다.
- PCRE backtrack 또는 recursion 한계가 매우 낮으면 올바른 입력을 거부하던 UTF-8 검증을 수정하고, 오프셋을 지역 변수로 전달하여 파서 부담을 줄였습니다.
- 내부 디스크립터를 확장과 공유하는 정수 테이프로 변경했습니다. 파서는 공백, 숫자, 문자열 구간을 바이트 범위 함수로 검사하고, 문자열 단위는 조회할 때 해석하며, 무의미한 공백과 중복 키가 없는 값은 원문 토큰을 복사하여 직렬화합니다. 결과, 오류, 오프셋은 바뀌지 않았습니다.
- 패키지 자체의 개발 절차, 변경 기록, Makefile, 문서 목록을 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.
- 네이티브 확장을 `php-extension` 패키지로 분리했으며 PHP 라이브러리는 독립적으로 사용할 수 있습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 저장소 루트의 [검증 기록](https://github.com/polyspec/ordered-json/blob/main/docs/operations/validation.ko.md#records)에서 설명합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

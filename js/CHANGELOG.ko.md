<!-- doc-id: changelog -->
<!-- source-sha256: b2676ff7afae3d9e80e2b2e003c44f9aabe1a1aaf0a2493e9f99c2f3f565e828 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- 파싱한 `Value`마다 `Object.freeze`를 호출하지 않도록 변경했습니다. private field로 값은 API로 변경할 수 없으며 `items`와 `keys` 배열은 계속 freeze합니다.
- 사용하지 않는 `stringify()` options 인자를 제거했습니다.
- 파서와 직렬화 부담을 줄였습니다. 값은 `WeakSet` 등록 대신 private field brand로 검사하고, escape가 없는 문자열은 원문에서 잘라 쓰며, 객체 키 토큰은 조회할 때 생성하고, 무의미한 공백과 중복 키가 없는 값은 원문 토큰으로 직렬화합니다. 결과, 오류, 오프셋은 바뀌지 않았습니다.
- 패키지 자체의 개발 절차, 변경 기록, Makefile, 문서 목록을 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 저장소 루트의 [검증 기록](https://github.com/polyspec/ordered-json/blob/main/docs/operations/validation.ko.md#records)에서 설명합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

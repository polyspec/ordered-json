<!-- doc-id: changelog -->
<!-- source-sha256: 89f2317a8fcd75907dd133b525fbe7f9d9a3ee08e658c06e5724e114c5baae39 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- 사용하지 않는 `stringify()` options 인자를 제거했습니다.
- 파서와 직렬화 부담을 줄였습니다. 값은 `WeakSet` 등록 대신 private field brand로 검사하고, escape가 없는 문자열은 원문에서 잘라 쓰며, 객체 키 토큰은 조회할 때 생성하고, 무의미한 공백과 중복 키가 없는 값은 원문 토큰으로 직렬화합니다. 결과, 오류, 오프셋은 바뀌지 않았습니다.
- 기존 구현 이력을 포함하는 독립 JavaScript 저장소를 구성했습니다.
- 명시한 커밋의 공통 검증기로 현재 후보 소스를 검사하는 단독 검사를 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 [공통 저장소](https://github.com/polyspec/ordered-json/blob/main/docs/verification.json)에서 관리합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

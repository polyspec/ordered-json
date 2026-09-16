<!-- doc-id: changelog -->
<!-- source-sha256: 43166fa4cbb6d46d117cc1dd6056d3faabea2b87d7107109d177b58f592f95a5 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- `Marshal`이 익명 구조체 필드를 버리지 않고 그 필드들을 펼쳐 넣고, 이름이 겹치는 필드는 중복 키를 만드는 대신 오류로 알리며, 파서의 중첩 한도에서 멈춰 순환 참조 값이 메모리를 소진하지 않고 오류를 반환합니다.
- 파서 할당을 줄였습니다. 값은 문서 구분자 수로 크기를 정한 묶음 단위로 할당하고, 문자열 단위는 조회할 때 해석하며, 멤버가 8개 이하인 객체는 선형 키 조회를 사용하고, 무의미한 공백과 중복 키가 없는 값은 원문 토큰을 복사하여 compact 출력을 만듭니다. `ParseBytesBorrowed` 입력에서 `Compact`와 `StringValue`가 반환하는 텍스트는 복사합니다. 결과, 오류, 오프셋은 바뀌지 않았습니다.
- 패키지 자체의 개발 절차, 변경 기록, Makefile, 문서 목록을 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.
- Go 모듈과 검사 어댑터 가져오기를 `github.com/polyspec/ordered-json/go`로 변경했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 저장소 루트의 [검증 기록](https://github.com/polyspec/ordered-json/blob/main/docs/operations/validation.ko.md#records)에서 설명합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

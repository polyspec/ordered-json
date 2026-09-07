<!-- doc-id: features -->
<!-- source-sha256: 22395885e1644f650b96aae9c4d241bc977013139e875621e57055040d72baa3 -->
# 기능 상태

[English](features.md)

<a id="state"></a>
## 현재 구현

`implemented`는 해당 동작이 구현됐다는 뜻입니다. `shared-suite`는 공통 JSON 테스트, `docs-tests`는 문서 검사기 테스트를 뜻합니다. [검증 기록](verification.json)에 실제 버전, 사례 수, 실행 시각, 소스 해시가 있습니다. `source-only`는 확인된 배포 방식이며 레지스트리 게시는 검증되지 않았습니다. 게시 확인 결과는 [distribution.json](distribution.json)에서 별도로 관리합니다.

| ID | 기능 | 구현 | 검증 | 근거 | 배포 | 명세 |
| --- | --- | --- | --- | --- | --- | --- |
| F-ORDER | 재귀 연관배열 객체; 최초 키 위치와 마지막 값 | implemented | shared-suite | [결과](verification.json) | source-only | [객체](spec/json-contract.ko.md#objects) |
| F-ARRAY | 배열 순서와 객체·배열 구분 | implemented | shared-suite | [결과](verification.json) | source-only | [배열](spec/json-contract.ko.md#arrays) |
| F-PARSE | JSON 문법, UTF-8 검사, 기본 중첩 제한 | implemented | shared-suite | [결과](verification.json) | source-only | [파싱](spec/json-contract.ko.md#parsing) |
| F-NUMBER | 정확한 숫자 토큰 | implemented | shared-suite | [결과](verification.json) | source-only | [숫자](spec/json-contract.ko.md#numbers) |
| F-STRING | 디코딩한 문자열과 이스케이프 surrogate 코드 단위 | implemented | shared-suite | [결과](verification.json) | source-only | [문자열](spec/json-contract.ko.md#strings) |
| F-OUTPUT | 연관배열 직렬화와 원문 조회 | implemented | shared-suite | [결과](verification.json) | source-only | [직렬화](spec/json-contract.ko.md#serialization) |
| F-CONSTRUCT | 순서 있는 연관배열과 Value 객체 배열로 생성 | implemented | shared-suite | [결과](verification.json) | source-only | [생성](spec/json-contract.ko.md#construction) |
| F-PHP-NATIVE | 공통 PHP API를 사용하는 PHP 확장 파서와 직렬화 | implemented | shared-suite | [결과](verification.json) | source-only | [PHP](spec/api.ko.md#php) |
| F-DOCS | 영한 문서, 링크·상태 검사, 검증 최신 여부 | implemented | docs-tests | [결과](verification.json) | source-only | [절차](documentation-plan.ko.md#checks) |

<a id="limits"></a>
## 검증 및 배포 한계

공통 사례 통과는 기록된 인수 기준에 대한 검증입니다. 모든 입력, 선언한 최소 런타임 전체, 모든 플랫폼, 모든 호스트 인코더 연동을 검증한 결과는 아닙니다. [검증 한계](operations/validation.ko.md#limits)를 확인합니다. 소스 메타데이터에는 개발 버전 문자열이 있으며 이 표는 레지스트리 릴리스를 나타내지 않습니다. 현재 이 표에 미완료로 표시한 구현 작업은 없습니다.

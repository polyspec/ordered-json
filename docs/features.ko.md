<!-- doc-id: features -->
<!-- source-sha256: 1a892fc401ee1ad52a513e07e16e85b022423c64f376a9c18a510ff3aa2349aa -->
# 기능 상태

[English](features.md)

<a id="state"></a>
## 현재 구현

`implemented`는 해당 동작이 구현됐다는 뜻입니다. `shared-suite`는 공통 JSON 테스트, `docs-tests`는 문서 검사기 테스트, `benchmark`는 저장소 벤치마크 프로토콜과 커밋된 결과를 뜻합니다. [검증 기록](verification.json)에 실제 버전, 사례 수, 실행 시각, 소스 해시가 있습니다. `source-only`는 확인된 배포 방식이며 레지스트리 게시는 검증되지 않았습니다. 게시 확인 결과는 [distribution.json](distribution.json)에서 별도로 관리합니다.

| ID | 기능 | 구현 | 검증 | 근거 | 배포 | 명세 |
| --- | --- | --- | --- | --- | --- | --- |
| F-ORDER | 재귀 연관배열 객체; 최초 키 위치와 마지막 값 | implemented | shared-suite | [결과](verification.json) | source-only | [객체](spec/json-contract.ko.md#objects) |
| F-ARRAY | 배열 순서와 객체·배열 구분 | implemented | shared-suite | [결과](verification.json) | source-only | [배열](spec/json-contract.ko.md#arrays) |
| F-PARSE | JSON 문법, UTF-8 검사, 기본 중첩 제한 | implemented | shared-suite | [결과](verification.json) | source-only | [파싱](spec/json-contract.ko.md#parsing) |
| F-NUMBER | 정확한 숫자 토큰 | implemented | shared-suite | [결과](verification.json) | source-only | [숫자](spec/json-contract.ko.md#numbers) |
| F-STRING | 디코딩한 문자열과 이스케이프 surrogate 코드 단위 | implemented | shared-suite | [결과](verification.json) | source-only | [문자열](spec/json-contract.ko.md#strings) |
| F-OUTPUT | 연관배열 직렬화와 원문 조회 | implemented | shared-suite | [결과](verification.json) | source-only | [직렬화](spec/json-contract.ko.md#serialization) |
| F-IDEMPOTENT | 반복 파싱과 직렬화에서 같은 타입 트리와 출력을 유지 | implemented | shared-suite | [결과](verification.json) | source-only | [직렬화](spec/json-contract.ko.md#serialization) |
| F-CONSTRUCT | 순서 있는 연관배열과 Value 객체 배열로 생성 | implemented | shared-suite | [결과](verification.json) | source-only | [생성](spec/json-contract.ko.md#construction) |
| F-PHP-NATIVE | 공통 PHP API를 사용하는 PHP 확장 파서와 직렬화 | implemented | shared-suite | [결과](verification.json) | source-only | [PHP](spec/api.ko.md#php) |
| F-DOCS | 영한 문서, 링크·상태 검사, 검증 최신 여부 | implemented | docs-tests | [결과](verification.json) | source-only | [절차](documentation-plan.ko.md#checks) |
| F-REPOS | 독립적으로 빌드할 수 있는 구현 패키지와 공통 적합성을 갖춘 단일 저장소 | implemented | shared-suite | [결과](verification.json) | source-only | [저장소](spec/repositories.ko.md) |
| F-BENCHMARK | 저장소 내부의 재현 가능한 벤치마크 프로토콜과 커밋된 결과 | implemented | benchmark | [결과](verification.json) | source-only | [벤치마크](../benchmarks/README.ko.md) |

<a id="limits"></a>
## 검증 및 배포 한계

이전 네이티브 macOS 및 PIE 기록은 기존 서브모듈 체크아웃에 해당하므로 이 모노레포의 현재 근거가 아닙니다. 로컬 PHAR가 준비되고 `make pie-check`가 통과한 뒤에만 새 PIE 기록을 생성합니다.

공통 사례 통과는 기록된 인수 기준에 대한 검증입니다. 모든 입력, 선언한 최소 런타임 전체, 모든 플랫폼, 모든 호스트 인코더 연동을 검증한 결과는 아닙니다. [검증 한계](operations/validation.ko.md#limits)를 확인합니다. 소스 메타데이터에는 개발 버전 문자열이 있으며 이 표는 레지스트리 릴리스를 나타내지 않습니다.

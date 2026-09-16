<!-- doc-id: changelog -->
<!-- source-sha256: ddd1caabf3aa57cc4f95520d90db5814c045f73c3ae891eea9e9785abada6119 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- 디스크립터 API의 패키지 테스트를 추가하고 구현 등록 정보에 선언했습니다. 하이드레이션한 멤버와 항목, 반복·escape 멤버 이름, `ValueError`로 거부하는 잘못된 디스크립터, compact 토큰 복사, 지원하는 깊이 범위, 보고하는 파싱 오류 위치를 다룹니다. 공통 사례는 PHP Value API를 통해서만 확장에 닿으므로, 이 표면은 이 테스트로만 검증합니다.
- `ordered_json_hydrate()`는 객체의 멤버만 반환하며 키 토큰용 값을 만들지 않습니다.
- 디스크립터로 컨테이너의 자식 `OrderedJson\Value` 객체를 만들고 소스와 맞지 않는 디스크립터를 `ValueError`로 거부하는 `ordered_json_hydrate()`를 추가했습니다. 하이드레이션은 별도 파일 `hydrate.c`로 컴파일하며, 클래스 조회는 요청마다 한 번 캐시합니다.
- `ordered_json_compact()`를 제거했습니다. PHP 라이브러리는 `ordered_json_compact_node()`로 직렬화합니다.
- 연관배열 디스크립터를 정수 테이프로 교체하고, 별도 선검증 대신 문자열을 검사하면서 UTF-8을 검증하되 잘못된 UTF-8을 다른 오류보다 먼저 보고하며, compact 하위 트리를 한 번의 복사로 직렬화합니다. `ordered_json_compact_node`는 디스크립터 인덱스를 받고 소스와 맞지 않는 디스크립터를 `ValueError`로 거부합니다. 형식은 [API 계약](https://github.com/polyspec/ordered-json/blob/main/docs/spec/api.ko.md#php)에 설명합니다. 파싱 결과, 오류, 오프셋은 바뀌지 않았습니다.
- macOS 번들 설정에서 누락된 배포 대상을 컴파일러로부터 구하고 사용하지 않는 동적 라이브러리 단일 모듈 플래그 검사를 제외합니다. 오래된 `-single_module` 및 `-undefined suppress` 링커 경고를 해결했습니다.
- 기존 구현 이력을 포함하는 독립 PHP extension 저장소를 구성했습니다.
- 명시한 커밋의 공통 검증기로 현재 후보 소스를 검사하는 단독 검사를 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.
- PIE `php-ext` 메타데이터, `src` 빌드 경로, 기본 활성화된 단독 빌드를 추가했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 [공통 저장소](https://github.com/polyspec/ordered-json/blob/main/docs/verification.json)에서 관리합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

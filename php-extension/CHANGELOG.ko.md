<!-- doc-id: changelog -->
<!-- source-sha256: 562aa1349dffe575650a4ae21df5d0931a13c33958f28c4bdf289cdda7663df3 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- `ordered_json_compact()`를 제거했습니다. PHP 라이브러리는 `ordered_json_compact_node()`로 직렬화합니다.
- 연관배열 디스크립터를 정수 테이프로 교체하고, 별도 선검증 대신 문자열을 검사하면서 UTF-8을 검증하되 잘못된 UTF-8을 다른 오류보다 먼저 보고하며, compact 하위 트리를 한 번의 복사로 직렬화합니다. `ordered_json_compact_node`는 디스크립터 인덱스를 받고 소스와 맞지 않는 디스크립터를 `ValueError`로 거부합니다. 형식은 [API 계약](https://github.com/polyspec/ordered-json/blob/main/docs/spec/api.ko.md#php)에 설명합니다. 파싱 결과, 오류, 오프셋은 바뀌지 않았습니다.
- macOS 번들 설정에서 누락된 배포 대상을 컴파일러로부터 구하고 사용하지 않는 동적 라이브러리 단일 모듈 플래그 검사를 제외합니다. 오래된 `-single_module` 및 `-undefined suppress` 링커 경고를 해결했습니다.
- 기존 구현 이력을 포함하는 독립 PHP extension 저장소를 구성했습니다.
- 명시한 커밋의 공통 검증기로 현재 후보 소스를 검사하는 단독 검사를 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.
- PIE `php-ext` 메타데이터, `src` 빌드 경로, 기본 활성화된 단독 빌드를 추가했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 [공통 저장소](https://github.com/polyspec/ordered-json/blob/main/docs/verification.json)에서 관리합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

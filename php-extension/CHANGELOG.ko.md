<!-- doc-id: changelog -->
<!-- source-sha256: 1ebe9c0ddc45ce11be5ea01aecfde661a629d52b9b31813210bcc7d5eee67aa0 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- macOS 번들 설정에서 누락된 배포 대상을 컴파일러로부터 구하고 사용하지 않는 동적 라이브러리 단일 모듈 플래그 검사를 제외합니다. 오래된 `-single_module` 및 `-undefined suppress` 링커 경고를 해결했습니다.
- 기존 구현 이력을 포함하는 독립 PHP extension 저장소를 구성했습니다.
- 명시한 커밋의 공통 검증기로 현재 후보 소스를 검사하는 단독 검사를 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.
- PIE `php-ext` 메타데이터, `src` 빌드 경로, 기본 활성화된 단독 빌드를 추가했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 [공통 저장소](https://github.com/ordered-json/ordered-json/blob/main/docs/verification.json)에서 관리합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

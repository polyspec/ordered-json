<!-- doc-id: changelog -->
<!-- source-sha256: 0c1e929216e924b81a41f4c528c642b50aa838790e1553609a738a5e2cdd2c9c -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- macOS 번들 설정에서 누락된 배포 대상을 컴파일러로부터 구하고 사용하지 않는 동적 라이브러리 단일 모듈 플래그 검사를 제외합니다. 오래된 `-single_module` 및 `-undefined suppress` 링커 경고를 해결했습니다.
- 패키지 자체의 개발 절차, 변경 기록, Makefile, 문서 목록을 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.
- PIE `php-ext` 메타데이터, `src` 빌드 경로, 기본 활성화된 단독 빌드를 추가했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 저장소 루트의 [검증 기록](https://github.com/polyspec/ordered-json/blob/main/docs/operations/validation.ko.md#records)에서 설명합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

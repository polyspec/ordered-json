<!-- doc-id: changelog -->
<!-- source-sha256: be1a03575d969d4498debbfb123f832aa7929a948bad569572e01334f02290d8 -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스

- 기존 구현 이력을 포함하는 독립 Go 저장소를 구성했습니다.
- 명시한 커밋의 공통 검증기로 현재 후보 소스를 검사하는 단독 검사를 추가했습니다.
- 영어와 한국어 사용 방법, 개발 절차, 변경 기록을 추가했습니다.
- Go 모듈과 검사 어댑터 가져오기를 `github.com/ordered-json/go`로 변경했습니다.

공통 JSON 동작은 유지합니다. `make check`로 검증 기록을 생성하며 통합 근거는 [공통 저장소](https://github.com/ordered-json/ordered-json/blob/main/docs/verification.json)에서 관리합니다. 여기서는 레지스트리 게시와 버전 릴리스를 선언하지 않습니다.

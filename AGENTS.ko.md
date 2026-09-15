<!-- doc-id: development -->
<!-- source-sha256: 6c41691419dacdc2114d1087a3193cb6e04f25b552a147723cc2db5541535982 -->
# 개발 절차

[English](AGENTS.md)

<a id="workflow"></a>
## 필수 작업 절차

수정 전에 [문서 관리](docs/documentation-plan.ko.md), 관련 [명세](docs/spec/json-contract.ko.md), [기능 상태](docs/features.ko.md)를 읽습니다. 동작을 변경하기 전에 명세를 갱신합니다. 완료하지 않은 작업은 기능 기록에 표시합니다.

올바른 코드와 사실에 맞는 이력을 유지합니다. 실제 원인을 직접 설명합니다. 코드 변경에 관련 문서, 기능 상태, 변경 기록을 포함합니다. 개인 선호, 대화 맥락, 인증 정보, 백업 위치는 Git 외부에서 관리합니다.

영어가 정본입니다. 같은 정보로 한국어 문서를 함께 갱신합니다. 번역 전체를 비교한 후에만 `source-sha256`을 갱신합니다. 문서, 주석, 커밋 메시지, 번역에는 주체와 동작을 명시한 직접적인 기술 표현을 사용합니다.

메시지 전송, 산출물 게시, 접근 제어 변경, 이력 재작성 권한을 임의로 해석하지 않습니다. 해당 작업에 이미 제공된 권한을 따릅니다. 사용자나 적용되는 지침이 명시적으로 요청하지 않았다면 하위 에이전트에 작업을 위임하지 않습니다.

<a id="verification"></a>
## 필수 검사

각 구현 패키지는 자체 소스와 문서 목록을 관리합니다. 저장소 루트에서 다음 명령을 실행합니다.

~~~sh
make check
git diff --check
~~~

전체 추가 사례를 포함하려면 다음 명령을 실행합니다.

~~~sh
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

문서만 검토할 때는 `make docs-check`를 실행합니다. 소스가 변경됐고 PIE 기록이 있으면 해당 추가 사례와 함께 `make pie-check PIE=/path/to/pie.phar`를 먼저 실행한 뒤 `make check`를 실행하여 현재 기록을 생성합니다. `make check`의 문서 검사는 오래된 PIE 기록을 거부합니다. 검사를 통과시키기 위해 검증 결과나 소스 해시를 직접 수정하지 않습니다.

[구현 등록 정보](implementations.json)는 패키지 경로·빌드·어댑터·런타임 명령을 정의합니다. 공통 JSON 비교 알고리즘을 변경하지 않고 해당 등록 정보와 패키지 디렉터리로 새 언어를 추가합니다. 계약 변경은 같은 저장소 리비전에서 검증기와 관련 패키지를 갱신합니다. [저장소 계약](docs/spec/repositories.ko.md)을 참조합니다.

모든 언어 어댑터는 [official.json](examples/official.json)과 [scripts/verify.py](scripts/verify.py)를 사용합니다. 공통 사례는 해당 파일이나 `fixtures/`에 추가합니다. 언어별로 다른 예제나 기대 결과를 만들지 않습니다.

Rust 코드를 변경하면 `rust/`에서 `cargo clippy --all-targets -- -D warnings`를 실행합니다. Go 코드를 변경하면 `go/`에서 `go vet ./...`를 실행합니다. 네이티브 코드를 변경하면 PHP 확장을 다시 빌드합니다. 이전 바이너리나 이전 결과를 변경된 코드의 검증 근거로 사용하지 않습니다.

<a id="completion"></a>
## 완료

코드와 테스트를 읽고 문서의 정확성을 확인합니다. 자동 링크, 개정본, 상태 검사는 문장 내용의 정확성을 증명하지 않습니다. 테스트와 실제 게시를 별도로 확인하고 관측한 근거로만 [배포 상태](docs/operations/distribution.ko.md)를 갱신합니다.

Git 메시지는 사실대로 간단하게 작성합니다. 관련 없는 변경은 가능하면 분리합니다. 작업을 완료하기 전에 Git 외부의 개인 메모리를 갱신합니다.

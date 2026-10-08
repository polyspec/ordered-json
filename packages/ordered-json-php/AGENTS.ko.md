<!-- doc-id: php-development -->
<!-- source-sha256: 9b9eae6a612c77b36622fa56bd346084a4d55fab574e880d6637bc165fededa2 -->
# 개발 절차

[English](AGENTS.md)

<a id="contract"></a>
## 계약과 문서

수정 전에 [사용 방법](README.ko.md)과 저장소의 공통 JSON 계약을 읽습니다. 동작을 바꾸기 전에 공통 명세를 갱신합니다. 공식 사례와 기대 결과는 저장소 루트에서 관리하며 이 패키지에 독립 기대값을 추가하지 않습니다.

영어가 정본입니다. 한국어 문서에 같은 정보를 반영하고 전체 번역을 검토한 뒤 `source-sha256`을 갱신합니다. 저장소 루트의 `make documents-check`가 모든 Markdown 문서를 읽습니다(`config/documents.json`). 개인 선호, 대화 맥락, 인증 정보, 백업 위치는 Git 외부에서 관리합니다. 주석과 커밋 메시지는 사실을 직접 작성합니다.

<a id="checks"></a>
## 필수 검사

저장소 루트 `AGENTS.md`의 필수 검사가 이 패키지에 적용됩니다. 개발 중에는 unit test만 실행합니다. 변경 중에는 RED 사례를 실행한 뒤 같은 사례를 GREEN까지 실행합니다. 이 디렉터리의 명령은 end-to-end 검사이며, hosted CI가 push 뒤에 전체 suite를 실행하고 어떤 규칙도 commit이나 push 전에 로컬 실행을 요구하지 않습니다.

~~~sh
make check
make docs-check
git diff --check
~~~

`make check`는 이 패키지만 공통 검증기로 검사하며(`scripts/verify.py --only`) 기록을 쓰지 않습니다. `make docs-check`는 저장소 루트의 `make documents-check`를 실행합니다. 저장소 루트의 구현 등록 정보 `implementations.json`이 이 패키지의 빌드, 패키지 테스트, 어댑터 명령을 선언합니다. 저장소 루트의 전체 suite는 `packages/ordered-json-rust/`에서 `cargo clippy --all-targets -- -D warnings`, `packages/ordered-json-go/`에서 `go vet ./...`을 실행합니다. 네이티브 소스를 변경하면 새로 빌드해야 하며 공통 네이티브 검사는 자동으로 다시 빌드합니다.

<a id="completion"></a>
## 완료

동작 변경에 문서와 변경 기록 수정을 포함합니다. 소스 게시는 테스트와 별도로 확인합니다.

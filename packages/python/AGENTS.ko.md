<!-- doc-id: python-development -->
<!-- source-sha256: 8bdaf478b4328f0dda86446ce7025bedb9397614133f436db89848086ba69115 -->
# 개발 절차

[English](AGENTS.md)

<a id="contract"></a>
## 계약과 문서

편집 전에 [사용법](README.ko.md)과 저장소의 공유 JSON 계약을 읽습니다. 동작 변경 전에 공유 명세를 먼저 갱신합니다. 공식 사례와 기대 결과는 저장소 루트에 둡니다. 이 패키지는 독립적인 기대값을 두지 않습니다.

영어가 원본입니다. 짝을 이루는 한국어 문서를 같은 정보로 갱신하고, 전체 번역을 대조한 뒤에만 `source-sha256`을 갱신합니다. 저장소 루트의 `make documents-check`가 모든 Markdown 문서를 읽습니다(`config/documents.json`). 개인 취향, 대화 맥락, 자격 증명, backup 위치는 Git 밖에 둡니다. 사실을 직접 말하는 comment와 commit message를 씁니다.

<a id="checks"></a>
## 필수 검사

저장소 루트 `AGENTS.md`의 필수 검사가 이 패키지에 적용됩니다. 개발 중에는 단위 test만 실행합니다. 변경 진행 중에는 RED 사례를 실행한 뒤 같은 사례를 GREEN으로 실행합니다. 이 디렉터리의 명령은 end-to-end 검사이고, push 뒤에 hosted CI가 전체 suite를 실행하며, commit이나 push 전 로컬 실행을 요구하는 규칙은 없습니다:

~~~sh
make check
make docs-check
git diff --check
~~~

`make check`는 이 패키지만 공통 검증기로 검사하며(`scripts/verify.mts --only`) 그 어댑터를 공통 사례와 비교하고 기록을 쓰지 않습니다. 패키지 테스트는 `make parity-check`가 실행하는 native 테스트입니다. `make docs-check`는 저장소 루트의 `make documents-check`를 실행합니다. 저장소 루트의 `config/parity.json`이 이 패키지를 unit과 함께 구현으로 선언하고, 그 unit의 native 테스트를 묶으며, `scripts/registry.mts`가 그 빌드와 어댑터 명령을 가집니다.

<a id="completion"></a>
## 완료

동작 변경에는 문서와 changelog 변경을 함께 넣습니다. source 게시는 검사와 별도로 확인합니다.

<!-- doc-id: python-development -->
<!-- source-sha256: a02d3d966e387717f744d04f99fa10bb264e6aed3908cc627a95094893dd49aa -->
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

`make check`는 이 패키지만 대상으로 공유 검증기를 실행하고(`scripts/verify.py --only`), `make docs-check`는 저장소 루트의 `make documents-check`를 실행합니다. 저장소 루트의 implementation registry `implementations.json`이 이 패키지의 패키지 test, 사례 목록, symbol 보고, adapter 명령을 선언합니다.

<a id="completion"></a>
## 완료

동작 변경에는 문서와 changelog 변경을 함께 넣습니다. source 게시는 검사와 별도로 확인합니다.

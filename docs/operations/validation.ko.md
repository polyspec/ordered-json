<!-- doc-id: validation -->
<!-- source-sha256: dd0704d1106c0301fce50c6bdf8a302322510ac9f2b5713059a59bf82b928109 -->
# 검증

[English](validation.md)

<a id="repository-check"></a>
## 저장소 검사

[필수 도구](installation.ko.md#requirements)를 설치한 후 저장소 루트에서 실행합니다.

~~~sh
make check
~~~

이 명령은 PHP 확장을 빌드하고 문서 검사기 테스트 및 JavaScript, Rust, Go, 순수 PHP, 네이티브 PHP의 동일 JSON 사례를 실행합니다. 검증 성공 후에만 [verification.json](../verification.json)을 작성하고 문서 검사를 실행합니다.

`verification.json`은 실제 런타임 버전, 사례 수, 구현별 결과, 문서 테스트 수, 소스 해시, 추가 입력 개정본을 기록합니다. 게시가 아닌 검증 기록입니다. 검사한 소스 파일이 바뀌면 현재 검증 근거로 사용할 수 없습니다. 검증기는 실행 중 소스가 변경되거나 일부 구현만 선택되면 기록 작성을 거부합니다.

<a id="supplementary"></a>
## 추가 입력

선택적인 추가 체크아웃은 재현을 위해 개정본을 고정합니다.

~~~sh
git clone https://github.com/nst/JSONTestSuite.git .cache/JSONTestSuite
git -C .cache/JSONTestSuite checkout 1ef36fa01286573e846ac449e8683f8833c5b26a
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

기록에는 추가 입력의 사용 여부를 표시합니다. `i_` 사례는 라이브러리의 UTF-8 및 깊이 정책을 적용합니다. 필요한 공식 기대값은 공통 소스에 있으며 언어 어댑터에는 별도 예제나 기대 결과가 없습니다.

<a id="individual"></a>
## 개별 구현

다음 명령은 선택한 구현을 같은 기대값으로 검사합니다. 저장소 검사를 대체하거나 전체 검증 기록을 갱신하지 않습니다.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/verify.py --only rust
python3 scripts/verify.py --only go
python3 scripts/verify.py --only php --only php-extension
~~~

마지막 명령을 실행하기 전에 네이티브 확장을 빌드해야 합니다. PHP 어댑터는 의도한 확장 파서가 로드됐는지 확인합니다.

<a id="documentation-checks"></a>
## 문서 검사

~~~sh
make docs-check
~~~

[검사기](../../scripts/docs_check.py)는 [목록](../documentation-manifest.json), 로컬 링크와 앵커, 번역 쌍과 개정본 해시, 섹션과 코드 블록의 일치, 기능 항목, 검증 근거 링크, 검증 결과의 최신 여부를 검사합니다. [테스트](../../scripts/tests/test_docs_check.py)는 유효한 문서와 의도적으로 만든 실패 사례를 검사합니다.

영어와 한국어 문장을 코드 및 테스트와 비교합니다. 그다음 한국어의 `source-sha256`을 영어 파일 전체의 SHA-256으로 갱신합니다. 검토 전에 마커를 갱신하지 않습니다. 외부 링크는 이 명령에서 문법만 검사하며 접속하지 않습니다.

<a id="limits"></a>
## 한계

테스트는 파서의 입력 허용 여부와 [인수 계약](../spec/json-contract.ko.md#acceptance)의 동작을 비교합니다. API 인자 전체, 기본값과 다른 모든 깊이 설정, 모든 최소 런타임 버전, 모든 플랫폼 빌드를 검증하지 않습니다. 라이브러리 직렬화 테스트는 모든 호스트 인코더의 동작을 검증하지 않습니다.

컴파일 경고와 검사 실패를 직접 보고합니다. 누락된 결과를 이전 실행으로 대체하지 않습니다. 후속 문서 검사가 실패해도 JSON 검증 성공 기록은 존재할 수 있습니다. 변경을 완료하기 전에 전체 `make check` 명령도 성공해야 합니다.

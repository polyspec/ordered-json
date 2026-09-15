<!-- doc-id: validation -->
<!-- source-sha256: cacdf5a331dacbebb042e64fc61a3b0597175f1b99c04647d74c61d0bbffcfc2 -->
# 검증

[English](validation.md)

<a id="repository-check"></a>
## 통합 검사

[필수 도구](installation.ko.md#requirements)를 설치하고 저장소 루트에서 실행합니다.

~~~sh
git submodule update --init --recursive
make check
~~~

검증기와 문서 검사기 테스트를 실행하고, 선택한 패키지를 빌드하고, 등록된 모든 구현에 공통 JSON 사례를 적용하고, [verification.json](../verification.json)을 생성한 뒤 공통·패키지 문서를 검사합니다. 통합 기록에는 추적된 모든 패키지 파일의 소스 해시가 포함됩니다.

기록에는 소스 해시, 패키지 파일 기록, 실제 런타임 버전, 사례 수, 결과, 검사기 테스트 수, 빌드 경고, 추가 입력 개정본이 포함됩니다. PHP 버전과 확장 버전은 별도 필드입니다. 입력이 변경되면 현재 검증 근거로 유효하지 않습니다. 실행 중 변경과 불완전한 구현 결과는 거부합니다. 이 기록은 게시 근거가 아닙니다.

<a id="supplementary"></a>
## 추가 입력

~~~sh
git clone https://github.com/nst/JSONTestSuite.git .cache/JSONTestSuite
git -C .cache/JSONTestSuite checkout 1ef36fa01286573e846ac449e8683f8833c5b26a
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

추가 입력 사용 여부를 기록합니다. `i_` 사례에는 공통 UTF-8·깊이 정책을 적용합니다. 공식 입력과 기대값은 공통 저장소에만 있으며 어댑터에 독립 기대값을 추가하지 않습니다.

<a id="individual"></a>
## 개별 구현

공통 체크아웃에서 선택한 검사는 정의된 어댑터를 빌드하고 실행합니다. 통합 기록은 갱신하지 않습니다.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/verify.py --only rust
python3 scripts/verify.py --only go
python3 scripts/verify.py --only php --only php-extension
~~~

독립 체크아웃은 다음과 같이 검사합니다.

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
make check
~~~

각 패키지는 독립 빌드 대상으로 유지하지만 공유 검사 명령은 루트 registry와 검증기가 정의합니다. 네이티브 확장은 `php-extension/`에서 빌드하며 같은 체크아웃의 형제 PHP 패키지와 함께 검사합니다.

추가 입력은 `make check JSON_TEST_SUITE=/path/to/JSONTestSuite`로 검사합니다. `make check HARNESS=/path/to/ordered-json`은 로컬 검증기를 명시적으로 선택하며 결과에 해당 지정을 기록합니다. 단독 결과에는 후보·의존성 소스 해시, 개정본, 로컬 수정 여부, 런타임 버전, 결과가 포함됩니다. 상위 결과는 더 새로운 후보 커밋의 검증 근거가 아닙니다.

<a id="pie"></a>
## PIE 산출물 검사

[공식 릴리스](https://github.com/php/pie/releases)에서 PIE PHAR를 내려받고 `gh attestation verify --owner php /path/to/pie.phar`로 출처를 확인합니다. 공통 루트에서 실행합니다.

~~~sh
make pie-check PIE=/path/to/pie.phar JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

[PIE 검사기](../../scripts/check_pie.py)는 `.cache/` 아래에 PIE 설정을 격리하고, 현재 확장 체크아웃을 경로 저장소로 등록하고, 패키지 인식을 확인하고, PIE로 빌드합니다. 같은 공통 어댑터와 기대값으로 해당 산출물을 직접 검사합니다. 중간에 일반 네이티브 빌드를 실행하지 않습니다.

준비된 경우 `pie-verification.json`은 PIE 버전과 PHAR 해시, 확장 산출물 해시, 명령, 소스 해시, PHP·확장 버전, 사례 결과를 기록합니다. 빌드 오류, 빌드 도구 누락, 어댑터 경고, 검사 중 변경은 검증 실패로 처리합니다. 컴파일 경고는 기록에 유지합니다. 이 검사는 모듈을 설치하거나 패키지를 게시하지 않습니다. 기록된 입력이 변경되면 다시 실행합니다.

<a id="documentation-checks"></a>
## 문서 검사

~~~sh
make docs-check
~~~

[검사기](../../scripts/docs_check.py)는 각 저장소의 문서 목록, 링크, 번역 쌍과 개정 해시, 절과 코드 블록 일치, 기능 상태, 현재 통합·PIE 근거를 검사합니다. 공통 목록에는 공통 문서만 등록합니다. 초기화된 구현 저장소는 자체 목록으로 검사합니다.

한국어 `source-sha256`을 갱신하기 전에 코드·테스트와 영어·한국어 내용을 비교합니다. 해시 일치는 번역 정확성을 증명하지 않습니다. 외부 링크는 문법만 검사하며 접속하지 않습니다. 호스팅 CI는 설정되지 않았으며 PR 제출이나 소스 게시 전에 필수 후보 검사를 실행해야 합니다.

<a id="limits"></a>
## 한계

사례 모음은 파서 허용 여부와 [인수 계약](../spec/json-contract.ko.md#acceptance)을 검사합니다. 모든 API 인수, 기본값이 아닌 모든 깊이 설정, 선언된 모든 최소 런타임, 모든 플랫폼, 모든 호스트 인코더 연동을 검증하지는 않습니다. Windows와 ZTS 네이티브 빌드는 검증되지 않았습니다.

실패한 검사와 컴파일 경고를 직접 기록합니다. 입력이 변경되면 이전 결과를 사용하지 않습니다. JSON 기록 생성 후 문서 검사가 실패할 수 있으므로 완료 전에 전체 검사가 성공해야 합니다.

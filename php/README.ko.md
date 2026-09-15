<!-- doc-id: overview -->
<!-- source-sha256: 0ccd4a92edd1bad4f2eb10c265e92ae1eb1e8b1bcc5dd53422df3f0887e326d8 -->
# ordered-json for PHP

[English](README.md)

객체를 연관배열로 처리하고 모든 깊이에서 문서 키 순서를 유지하는 엄격한 JSON 구현입니다. 중복 키는 최초 위치와 마지막 값을 유지합니다. 공식 입력과 기대 결과는 모노레포의 examples에서 관리합니다.

<a id="usage"></a>
## 사용

JSON 및 PCRE를 제공하는 PHP >= 8.2를 요구하며 Composer 패키지는 `ordered-json/ordered-json`입니다.

사용 코드의 `source` 또는 `$source`는 [공통 공식 예제](https://github.com/polyspec/ordered-json/blob/main/examples/official.json)의 객체 사례에서 가져옵니다.

~~~php
require 'src/OrderedJson.php';
$value = OrderedJson\parse($source);
$output = OrderedJson\stringify($value);
~~~


[네이티브 확장](https://github.com/polyspec/ordered-json/php-extension)은 별도의 선택적 패키지입니다. 순수 PHP에는 확장 체크아웃이 필요하지 않습니다. `parse(..., useNative: false)`는 순수 파서를 선택하며 확장이 로드되어 있으면 `compact()`는 네이티브 직렬화를 사용합니다. 순수 구현 테스트는 `php -n`을 사용합니다.

동작은 [JSON 계약](https://github.com/polyspec/ordered-json/blob/main/docs/spec/json-contract.ko.md)과 [API 계약](https://github.com/polyspec/ordered-json/blob/main/docs/spec/api.ko.md)에 정의합니다. 소스는 이 저장소에서 제공합니다. 레지스트리 게시와 버전 릴리스는 검증되지 않았으며 소스 버전 문자열은 릴리스 기록이 아닙니다.

<a id="verification"></a>
## 검증

Python >= 3.9, Git, make, 해당 구현의 런타임·빌드 도구를 설치하고 이 체크아웃에서 실행합니다.

~~~sh
make check
~~~

루트 검증기를 호출하여 이 패키지를 검사합니다. 루트 통합 검사는 같은 소스 리비전의 모든 패키지를 검사하고 현재 결과를 `docs/verification.json`에 기록합니다.

추가 사례는 `make check JSON_TEST_SUITE=/path/to/JSONTestSuite`로 검사합니다. 검증기 공동 개발에는 `make check HARNESS=/path/to/ordered-json`을 사용하며 결과에 로컬 지정 여부를 기록합니다. [개발 절차](AGENTS.ko.md)와 [변경 기록](CHANGELOG.ko.md)에 필수 검사와 변경 사항이 있습니다.

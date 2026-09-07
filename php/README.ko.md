<!-- doc-id: php -->
<!-- source-sha256: 57cdb70e07813f151d7237cc329b42d4447468bfc3dfe142d85db643a3bbc1a6 -->
# PHP

[English](README.md)

<a id="usage"></a>
## 사용

순수 PHP 패키지와 선택적 [네이티브 확장](../php-extension/README.ko.md)은 같은 `Value` API를 사용합니다. 요구사항과 로드 방법은 [설치](../docs/operations/installation.ko.md)를 확인합니다. 여기서 `$source`는 [official.json](../examples/official.json)의 객체 사례에 있는 `input` 문자열이며 파일 경로는 이 디렉터리 기준입니다.

~~~php
require 'src/OrderedJson.php';

$value = OrderedJson\parse($source);
$members = $value->members();
$output = OrderedJson\stringify($value);
$rebuilt = OrderedJson\stringify(OrderedJson\Value::object($members));
~~~

`members()`는 라이브러리 값의 연관배열을 반환합니다. 연관배열에는 `Value::object`를, JSON 배열에는 `Value::array`를 사용합니다. 라이브러리의 `stringify`를 사용합니다. `json_encode($value)`는 예외를 발생시킵니다. [API 계약](../docs/spec/api.ko.md#php)에 파싱과 네이티브 직렬화의 개별 규칙을 포함한 백엔드 선택을 정의합니다.

<a id="verification"></a>
## 검증

확장을 빌드한 뒤 저장소 루트에서 실행합니다.

~~~sh
python3 scripts/verify.py --only php --only php-extension
~~~

두 백엔드는 공통 검증기와 공식 기대 결과를 사용합니다. [저장소 검사](../docs/operations/validation.ko.md)는 확장을 빌드하고 모든 구현을 검사합니다.

# PHP

PHP 8.2 이상. `src/OrderedJson.php`를 불러오거나 이 디렉터리를 Composer path 저장소로 사용합니다.

`$source`는 [공식 예제](../examples/official.json)의 `input` JSON 문자열입니다.

```php
require 'src/OrderedJson.php';

$value = OrderedJson\parse($source);
$members = $value->members(); // list<Member>, 문서 순서
$output = OrderedJson\stringify($value);
```

객체는 `Value::object([new Member($key, $value), ...])`, 배열은 `Value::array([$value, ...])`로 구성합니다. 키는 문자열 종류의 `Value`입니다. 스칼라는 `Value::string`, `Value::number`, `Value::boolean`, `Value::null`로 생성합니다.

`items()`는 배열 원소, `get()`·`getAll()`은 객체 이름 조회입니다. `stringUnits()`는 손실 없는 UTF-16 단위를 반환합니다. `stringValue()`는 단독 surrogate가 있으면 오류를 반환합니다. 숫자는 `numberLiteral()`로 조회합니다.

`OrderedJson\stringify($value, compact: true)`는 공백을 제거합니다. 깊이 제한은 `OrderedJson\parse($source, maxDepth: 256)`으로 설정합니다. 직렬화에는 패키지의 `stringify`를 사용합니다. `json_encode($value)`는 내부 노드의 잘못된 출력을 방지하기 위해 오류를 반환합니다.

## 순수 PHP와 네이티브 확장

동일한 API를 사용합니다. [ordered_json 확장](ext/README.md)이 로드되어 있으면 C 파서를 사용하고, 없으면 순수 PHP 파서를 사용합니다.

- `OrderedJson\parse($source, useNative: false)`: 순수 PHP 파서 지정
- `OrderedJson\parseNative($source)`: C 파서 지정. 확장이 없으면 오류

네이티브 버전은 파싱과 공백 제거를 C에서 수행합니다. 순서 있는 `Value` API는 공통 PHP 코드입니다.

저장소 루트에서 두 구현을 동일한 공식 예제로 검증합니다.

```sh
python3 scripts/verify.py --only php --only php-native
```

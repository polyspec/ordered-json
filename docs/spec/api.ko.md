<!-- doc-id: api -->
<!-- source-sha256: 18fe09943999d56e672b9195743c55a2bb6785177097b07d324dec1ebc089ed4 -->
# API 계약

[English](api.md)

[JSON 계약](json-contract.ko.md)은 모든 구현의 공통 동작을 정의합니다. 이 문서는 현재 언어별 API를 정의합니다. 현재 식별자는 [설치 문서](../operations/installation.ko.md)에 작성합니다.

프로젝트와 패키지 이름은 `ordered-json`입니다. Rust 가져오기는 `ordered_json`을 사용합니다. Go는 `github.com/polyspec/ordered-json/go` 모듈과 `orderedjson` 패키지를 사용합니다. PHP는 `ordered-json/ordered-json` Composer 패키지, `OrderedJson` 네임스페이스, `ordered_json` 확장을 사용합니다. 네이티브 함수와 상수 접두사는 `ordered_json_`과 `ORDERED_JSON_`입니다.

<a id="values"></a>
## 값과 파싱

파싱된 `Value` 객체는 불변입니다. 생성자는 문자열, 숫자 토큰, 불리언, null, 배열, 객체를 생성합니다. 생성자는 라이브러리 parser를 통해 값을 검사합니다. 종류가 맞지 않는 접근은 접근자에 따라 값 없음 또는 오류를 반환하며 잘못된 생성 인자는 언어별 오류를 발생시킵니다. 핵심 parser와 serializer는 JSON 동작을 host JSON API에 위임하지 않습니다.

| 동작 | JavaScript | Rust | Go | PHP |
| --- | --- | --- | --- | --- |
| 텍스트 파싱 | `parse(source, options)` | `parse(source)` | `Parse(source)` | `parse(source, maxDepth, useNative)` |
| UTF-8 바이트 | `parseBytes(bytes, options)` | `parse_bytes(bytes)` | `ParseBytes(bytes)` / `ParseBytesBorrowed(bytes)` | `parse(source)` |
| 깊이 한도 | `options.maxDepth` | `parse_with_max_depth(source, limit)` | `ParseWithMaxDepth(source, limit)` | `maxDepth` |
| 기본 출력 | `stringify(value)` | `stringify(&value)` | `Stringify(value)` | `stringify($value)` |
| compact 출력 | `stringify(value)` | `value.compact()` | `value.Compact()` | `$value->compact()` |
| 원문 조회 | `value.raw` | `value.raw()` | `value.Raw()` | `$value->raw()` |
| 종류 | `value.kind` | `value.kind()` | `value.Kind()` | `$value->kind()` |

JavaScript 파싱 오류는 UTF-16 위치를 반환합니다. Rust, Go, PHP 파싱 오류는 UTF-8 바이트 위치를 반환합니다. Go `Value`의 영값은 유효하지 않습니다. Rust와 Go의 빈 `OrderedMap`은 유효한 객체 입력입니다.

<a id="objects"></a>
## 연관 객체

| 동작 | JavaScript | Rust | Go | PHP |
| --- | --- | --- | --- | --- |
| 멤버 연관배열 | `value.members` | `value.members()` | `value.Members()` | `$value->members()` |
| 문자열 키 조회 | `value.get(key)` | `value.get(key)` | `value.Get(key)` | `$value->get($key)` |
| 코드 단위 조회 | `value.get(key)` | `value.get_units(units)` | `value.GetUnits(units)` | `$value->getUnits($units)` |
| 객체 생성 | `Value.object(entries)` | `Value::object(&map)` | `Object(map)` | `Value::object($map)` |

JavaScript는 복사된 `Map<string, Value>`를 반환하며 TypeScript에는 `ReadonlyMap`으로 노출합니다. `value.keys`는 첫 번째로 파싱된 키 토큰을 순서대로 반환합니다. 객체 생성자는 `[string or Value, Value]` 항목의 iterable을 받습니다.

Rust는 불변 `OrderedMap` 참조를 반환합니다. `OrderedMap::insert(key, value)`는 문자열 `Value` 키를 받고 교체된 값이 있으면 반환합니다. `iter()`는 등록 순서대로 키와 값의 참조를 반환합니다.

Go는 독립적인 `OrderedMap` 복사본을 반환합니다. `Set(key, value)`는 문자열 `Value` 키를 받으며 `Keys()`는 등록 순서대로 키 값을 반환합니다. `Get`과 `GetUnits`는 값 포인터 또는 nil을 반환합니다. `ParseBytes`는 입력을 복사합니다. `ParseBytesBorrowed`는 명시적인 zero-copy API이며 반환된 값이 살아 있는 동안 호출자는 바이트 슬라이스를 변경하면 안 됩니다. `ParseMany(source)`와 `ParseManyWithMaxDepth(source, limit)`는 JSON Lines처럼 공백으로 구분된 JSON 값 시퀀스를 파싱하여 문서마다 루트 값 하나를 반환하며, 잘못된 값이 하나라도 있으면 전체 입력을 거부합니다.

PHP는 `Value` 객체의 연관배열을 반환합니다. 객체 생성자는 해당 연관배열을 받습니다. 키가 없으면 PHP는 null, JavaScript는 undefined, Rust는 `None`, Go는 nil을 반환합니다.

<a id="scalars"></a>
## 배열과 스칼라

| 동작 | JavaScript | Rust | Go | PHP |
| --- | --- | --- | --- | --- |
| 배열 생성 | `Value.array(items)` | `Value::array(items)` | `Array(items)` | `Value::array($items)` |
| 배열 원소 | `value.items` | `value.items()` | `value.Items()` | `$value->items()` |
| 문자열 생성 | `Value.string(text)` | `Value::string(text)` | `String(text)` | `Value::string($text)` |
| 문자열 조회 | `stringValue()` | `string_value()` | `StringValue()` | `stringValue()` |
| UTF-16 조회 | `stringUnits()` | `string_units()` | `StringUnits()` | `stringUnits()` |
| UTF-16 생성 | `Value.string(text)` | `Value::from_units(units)` | `StringFromUnits(units)` | `Value::fromUnits($units)` |
| 숫자 생성 | `Value.number(token)` | `Value::number(token)` | `Number(token)` | `Value::number($token)` |
| 숫자 조회 | `numberLiteral()` | `number_literal()` | `NumberLiteral()` | `numberLiteral()` |
| 불리언 생성 | `Value.boolean(flag)` | `Value::boolean(flag)` | `Boolean(flag)` | `Value::boolean($flag)` |
| 불리언 조회 | `booleanValue()` | `boolean_value()` | `BooleanValue()` | `booleanValue()` |
| null 생성 | `Value.null()` | `Value::null()` | `Null()` | `Value::null()` |

JavaScript는 기존 UTF-16 텍스트로 문자열을 생성할 수 있습니다. Rust와 Go는 UTF-16 단위를 슬라이스로 제공하며 PHP는 정수 코드 단위 목록을 요구합니다. 배열 조회는 불변 데이터 또는 독립적인 복사본을 반환합니다.

<a id="php"></a>
## PHP 파서

`OrderedJson\parse`는 `ordered_json` 확장이 로드돼 있으면 네이티브 파서를 사용합니다. `useNative: false`는 순수 PHP 파싱을 선택합니다. `OrderedJson\parseNative`는 확장을 요구하며 확장이 없으면 실패합니다. 공통 `Value` API는 루트 파서 디스크립터만 보유하고 트리 접근이 필요할 때 자식 값을 지연 생성합니다.

확장이 로드돼 있으면 `useNative: false`로 파싱한 값도 `compact()`에서 네이티브 직렬화를 사용합니다. 두 동작 모두 순수 PHP로 실행하려면 해당 확장 없이 PHP를 실행합니다.

확장은 `ordered_json_scan(source, maxDepth)`, `ordered_json_compact(source, maxDepth)`, `ordered_json_compact_node(source, descriptor, index)`를 제공합니다. 디스크립터는 문서 순서대로 값마다 `meta`, `start`, `end` 세 정수를 담은 목록입니다. `start`와 `end`는 값 토큰의 바이트 범위이며 첫 항목은 원문이 전체 소스인 루트 값입니다. `meta`는 0–2비트에 종류(1 object, 2 array, 3 string, 4 number, 5 boolean, 6 null), 3–5비트에 플래그, 8비트부터 연결 인덱스를 저장합니다. compact 플래그(8)는 무의미한 공백과 중복 키가 없는 값을 표시하며 이 값의 compact 출력은 토큰과 같습니다. escaped 플래그(16)는 escape 시퀀스가 있는 문자열 토큰을 표시하며 UTF-16 단위는 조회할 때 해석합니다. 컨테이너는 마지막 하위 값 다음 항목을 연결합니다. 객체 멤버는 키 항목 뒤에 값이 이어지며 키는 멤버가 유지하는 값을 연결합니다. 반복된 키에는 skip 플래그(32)가 있으며 같은 이름의 첫 키가 마지막 값을 연결합니다. 네이티브 파싱 실패는 `OrderedJsonNativeParseError`를 사용하며 공통 API가 이를 `OrderedJson\ParseError`로 변환합니다. `ordered_json_compact_node`는 소스와 맞지 않는 디스크립터를 `ValueError`로 거부합니다.

네이티브 빌드는 PHP 버전, 플랫폼, 스레드 안전 설정과 일치해야 합니다. [네이티브 설치](../operations/installation.ko.md#native-php)를 확인합니다.

# Rust

의존성 없는 Rust 라이브러리입니다. 로컬 Cargo 의존성의 `path`를 이 디렉터리로 지정합니다.

`source`는 [공식 예제](../examples/official.json)의 `input` JSON 문자열입니다.

```rust
use ordered_json::{parse, stringify};

let value = parse(source)?;
let members = value.members().expect("object"); // &OrderedMap, 키의 첫 등장 순서
let output = stringify(&value);
```

객체는 `OrderedMap::new()`로 연관배열을 만든 뒤 `insert(key, value)`로 채우고 `Value::object(&members)`에 전달합니다. 키는 문자열 종류의 `Value`입니다. `iter()`는 키의 첫 등장 순서를 따르며 같은 키를 다시 넣으면 값만 덮어씁니다. 배열은 `Value::array(&[Value, ...])`로 구성합니다. 스칼라는 `Value::string`, `Value::number`, `Value::boolean`, `Value::null`로 생성합니다.

`items()`는 배열 원소, `get()`은 객체 키의 마지막 값 조회입니다. `string_units()`는 손실 없는 UTF-16 단위를 반환합니다. `string_value()`는 단독 surrogate가 있으면 오류를 반환합니다. 숫자는 `number_literal()`로 조회합니다.

`parse_bytes()`는 UTF-8 바이트 입력, `parse_with_max_depth()`는 깊이 제한 설정입니다. `stringify()`와 `compact()`는 연관배열을 공백 없는 JSON으로 출력하여 `String`을 반환합니다. `raw()`는 입력 원문 조회입니다.

저장소 루트에서 공통 공식 예제를 검증합니다.

```sh
python3 scripts/verify.py --only rust
```

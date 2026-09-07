<!-- doc-id: rust -->
<!-- source-sha256: 03ca1e5491307f033948c444b82f3bb1ff5a0dcd4b6d539cac72691ece6fb79c -->
# Rust

[English](README.md)

<a id="usage"></a>
## 사용

이 크레이트는 의존성이 없습니다. 요구사항과 로컬 Cargo 의존성 설정은 [설치](../docs/operations/installation.ko.md)를 확인합니다. 아래 코드는 오류를 반환할 수 있는 함수의 일부이며 `source`는 [official.json](../examples/official.json)의 객체 사례에 있는 `input` 문자열입니다.

~~~rust
use ordered_json::{parse, stringify, Value};

let value = parse(source)?;
let members = value.members().expect("object");
let output = stringify(&value);
let rebuilt = stringify(&Value::object(members)?);
~~~

`members`는 불변 `OrderedMap` 참조입니다. `OrderedMap`을 생성하고 문자열 `Value` 키와 자식 값을 삽입한 뒤 `Value::object`를 호출합니다. 값 슬라이스에는 `Value::array`를 사용합니다. 스칼라 생성, 바이트 파싱, 코드 단위, 오류 동작은 [API 계약](../docs/spec/api.ko.md)을 확인합니다.

<a id="verification"></a>
## 검증

저장소 루트에서 실행합니다.

~~~sh
python3 scripts/verify.py --only rust
~~~

공통 검증기와 공식 기대 결과를 사용합니다. [저장소 검사](../docs/operations/validation.ko.md)는 모든 구현을 검사합니다.

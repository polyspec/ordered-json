# Go

Go 1.22 이상, 외부 의존성 없는 모듈입니다. 로컬 프로젝트의 `go.mod`에서 `github.com/ordered-json/ordered-json/go` 모듈을 이 디렉터리로 `replace`하여 사용합니다.

`source`는 [공식 예제](../examples/official.json)의 `input` JSON 문자열입니다.

```go
value, err := orderedjson.Parse(source)
if err != nil { return err }
members, err := value.Members() // *OrderedMap, 키의 첫 등장 순서
if err != nil { return err }
output, err := orderedjson.Stringify(value)
```

객체는 `&orderedjson.OrderedMap{}`으로 연관배열을 만든 뒤 `Set(key, value)`로 채우고 `orderedjson.Object(members)`에 전달합니다. 키는 문자열 종류의 `Value`입니다. `Keys()`는 키의 첫 등장 순서를 따르며 같은 키를 다시 넣으면 값만 덮어씁니다. 배열은 `orderedjson.Array([]*orderedjson.Value{...})`로 구성합니다. 스칼라는 `String`, `Number`, `Boolean`, `Null`로 생성합니다.

`Items()`는 배열 원소, `Get()`은 객체 키의 마지막 값 조회입니다. `Members()`는 연관배열 복사본을 반환하므로 수정해도 원래 `Value`에 영향을 주지 않습니다. `StringUnits()`는 손실 없는 UTF-16 단위를 반환합니다. `StringValue()`는 단독 surrogate가 있으면 오류를 반환합니다. 숫자는 `NumberLiteral()`로 조회합니다.

`ParseBytes()`는 UTF-8 바이트 입력, `Compact()`는 공백 제거 출력, `ParseWithMaxDepth()`는 깊이 제한 설정입니다. `Value`의 영값은 유효한 JSON 값이 아닙니다.

`orderedjson.Stringify`와 `Compact()`는 연관배열을 공백 없는 JSON으로 출력합니다. `Raw()`는 입력 원문 조회입니다. `encoding/json.Marshal(value)` 연동도 지원하며 키 순서를 유지합니다. 표준 `encoding/json`은 HTML 관련 이스케이프를 바꿀 수 있습니다.

저장소 루트에서 공통 공식 예제를 검증합니다.

```sh
python3 scripts/verify.py --only go
```

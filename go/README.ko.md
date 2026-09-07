<!-- doc-id: go -->
<!-- source-sha256: dc04058bbf50051ae671ea4905443b3dc5487c18007324e329d7ebbd5c03ad61 -->
# Go

[English](README.md)

<a id="usage"></a>
## 사용

이 모듈은 외부 의존성이 없습니다. 요구사항과 로컬 모듈 대체 설정은 [설치](../docs/operations/installation.ko.md)를 확인합니다. 아래 함수 코드에서 `github.com/ordered-json/ordered-json/go`를 가져오고 [official.json](../examples/official.json)의 객체 사례에 있는 `input` 문자열을 `source`로 사용합니다. 코드를 포함한 함수는 오류를 반환합니다.

~~~go
value, err := orderedjson.Parse(source)
if err != nil { return err }
members, err := value.Members()
if err != nil { return err }
output, err := orderedjson.Stringify(value)
if err != nil { return err }
rebuilt, err := orderedjson.Object(members)
if err != nil { return err }
_ = output
_ = rebuilt
~~~

`Members()`는 독립 `OrderedMap` 복사본을 반환합니다. `Set`에는 문자열 `Value` 키를, `Object`에는 연관배열을, `Array`에는 값 포인터 슬라이스를 사용합니다. 나머지 동작은 [API 계약](../docs/spec/api.ko.md)을 확인합니다. `encoding/json.Marshal`은 `MarshalJSON`으로 이 값을 지원하지만 HTML 이스케이프를 바꿀 수 있습니다. 라이브러리 직렬화는 [JSON 계약](../docs/spec/json-contract.ko.md#serialization)에 정의합니다.

<a id="verification"></a>
## 검증

저장소 루트에서 실행합니다.

~~~sh
python3 scripts/verify.py --only go
~~~

공통 검증기와 공식 기대 결과를 사용합니다. [저장소 검사](../docs/operations/validation.ko.md)는 모든 구현을 검사합니다.

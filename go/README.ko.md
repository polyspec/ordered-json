<!-- doc-id: overview -->
<!-- source-sha256: 03449c3961fb06b36664d2d69afbe604ec2f557206717e67d2b67646c8f22bd4 -->
# ordered-json for Go

[English](README.md)

객체를 연관배열로 처리하고 모든 깊이에서 문서 키 순서를 유지하는 엄격한 JSON 구현입니다. 중복 키는 최초 위치와 마지막 값을 유지합니다. 공식 입력과 기대 결과는 모노레포의 examples에서 관리합니다.

<a id="usage"></a>
## 사용

Go >= 1.22이며 모듈은 `github.com/ordered-json/go`, 패키지는 `orderedjson`입니다.

사용 코드의 `source` 또는 `$source`는 [공통 공식 예제](https://github.com/ordered-json/ordered-json/blob/68963b9da95dd2bdb6adcb7d3b305b25190bafb0/examples/official.json)의 객체 사례에서 가져옵니다. `github.com/ordered-json/go`를 가져오고 오류를 반환할 수 있는 함수 안에서 사용합니다.

~~~go
value, err := orderedjson.Parse(source)
if err != nil { return err }
output, err := orderedjson.Stringify(value)
if err != nil { return err }
_ = output
~~~


동작은 [JSON 계약](https://github.com/ordered-json/ordered-json/blob/68963b9da95dd2bdb6adcb7d3b305b25190bafb0/docs/spec/json-contract.ko.md)과 [API 계약](https://github.com/ordered-json/ordered-json/blob/68963b9da95dd2bdb6adcb7d3b305b25190bafb0/docs/spec/api.ko.md)에 정의합니다. 소스는 이 저장소에서 제공합니다. 레지스트리 게시와 버전 릴리스는 검증되지 않았으며 소스 버전 문자열은 릴리스 기록이 아닙니다.

<a id="verification"></a>
## 검증

Python >= 3.9, Git, make, 해당 구현의 런타임·빌드 도구를 설치하고 이 체크아웃에서 실행합니다.

~~~sh
make check
~~~

루트 검증기를 호출하여 이 패키지를 검사합니다. 루트 통합 검사는 같은 소스 리비전의 모든 패키지를 검사하고 현재 결과를 `docs/verification.json`에 기록합니다.

추가 사례는 `make check JSON_TEST_SUITE=/path/to/JSONTestSuite`로 검사합니다. 검증기 공동 개발에는 `make check HARNESS=/path/to/ordered-json`을 사용하며 결과에 로컬 지정 여부를 기록합니다. [개발 절차](AGENTS.ko.md)와 [변경 기록](CHANGELOG.ko.md)에 필수 검사와 변경 사항이 있습니다.

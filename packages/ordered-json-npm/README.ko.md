<!-- doc-id: npm-overview -->
<!-- source-sha256: 2b8f9d169b754db22c6423f52c98e65639dd2527f5d63b968ff0fe1d7a4f5029 -->
# ordered-json for JavaScript

[English](README.md)

객체를 연관배열로 처리하고 모든 깊이에서 문서 키 순서를 유지하는 엄격한 JSON 구현입니다. 중복 키는 최초 위치와 마지막 값을 유지합니다. 공식 입력과 기대 결과는 모노레포의 examples에서 관리합니다.

<a id="usage"></a>
## 사용

Node.js >= 20이며 ESM과 TypeScript 선언을 제공합니다.

사용 코드의 `source` 또는 `$source`는 [공통 공식 예제](https://github.com/polyspec/ordered-json/blob/main/examples/official.json)의 객체 사례에서 가져옵니다.

~~~js
import {parse, stringify} from './index.js';
const value = parse(source);
const members = value.members;
const output = stringify(value);
~~~

`parse(source, {rejectDuplicates: true})`와 `parseBytes(bytes, {rejectDuplicates: true})`는 마지막 값을 유지하지 않고 어느 깊이든 해석된 객체 키가 반복되면 `duplicate_object_key` 종류의 `ParseError`로 거부합니다.

동작은 [JSON 계약](https://github.com/polyspec/ordered-json/blob/main/docs/spec/json-contract.ko.md)과 [API 계약](https://github.com/polyspec/ordered-json/blob/main/docs/spec/api.ko.md)에 정의합니다. 소스는 이 저장소에서 제공합니다. 레지스트리 게시와 버전 릴리스는 검증되지 않았으며 소스 버전 문자열은 릴리스 기록이 아닙니다.

<a id="verification"></a>
## 검증

`.python-version`이 지정한 minor release의 Python, Git, make, 해당 구현의 런타임·빌드 도구를 설치하고 이 체크아웃에서 실행합니다.

~~~sh
make check
~~~

루트 검증기를 호출하여 이 패키지를 검사합니다. 루트 통합 검사는 같은 소스 리비전의 모든 패키지를 검사하고 현재 결과를 그 실행의 기록인 `var/records/verification.json`에 기록합니다.

추가 사례는 `make check JSON_TEST_SUITE=/path/to/JSONTestSuite`로 검사합니다. [개발 절차](AGENTS.ko.md)와 [변경 기록](CHANGELOG.ko.md)에 필수 검사와 변경 사항이 있습니다.

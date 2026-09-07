<!-- doc-id: javascript -->
<!-- source-sha256: 3ef0e7465fc00eaa9330b41347f4dc28291d597f10c6e303ec293e911b29a66a -->
# JavaScript

[English](README.md)

<a id="usage"></a>
## 사용

런타임 의존성 없이 ESM과 TypeScript 선언을 제공합니다. 런타임 요구사항과 소스 사용 방법은 [설치](../docs/operations/installation.ko.md)를 확인합니다. 아래 코드의 `source`는 [official.json](../examples/official.json)의 객체 사례에 있는 `input` 문자열입니다. 가져오기 경로는 이 디렉터리 기준입니다.

~~~js
import {parse, stringify, Value} from './index.js';

const value = parse(source);
const members = value.members;
const keys = [...members.keys()];
const output = stringify(value);
const rebuilt = stringify(Value.object(members));
~~~

`members`는 `Map<string, Value>` 복사본입니다. `Value.object`에 순서 있는 항목을, `Value.array`에 라이브러리 값 배열을 전달합니다. 파싱, 스칼라 생성, 조회, 직렬화는 [API 계약](../docs/spec/api.ko.md)에 정의합니다. 라이브러리의 `stringify`를 사용합니다. `JSON.stringify(value)`는 예외를 발생시킵니다.

<a id="verification"></a>
## 검증

이 디렉터리에서 실행합니다.

~~~sh
npm test
~~~

공통 검증기와 공식 기대 결과를 사용합니다. [저장소 검사](../docs/operations/validation.ko.md)는 모든 구현을 검사합니다.

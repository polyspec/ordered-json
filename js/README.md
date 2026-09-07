# JavaScript

Node.js 20 이상. 런타임 의존성 없이 ESM과 TypeScript 타입 정의를 제공합니다.

`source`는 [공식 예제](../examples/official.json)의 `input` JSON 문자열입니다.

```js
import {parse, stringify, Value} from './index.js';

const value = parse(source);
const members = value.members; // [{key: Value, value: Value}, ...], 문서 순서
const keys = members.map(member => member.key.stringValue());
const output = stringify(value);
```

객체는 `Value.object([[문자열키, Value], ...])`, 배열은 `Value.array([Value, ...])`로 구성합니다. 문자열·숫자·불리언·null 생성은 `Value.string`, `Value.number`, `Value.boolean`, `Value.null`을 사용합니다. `Value.number`에는 숫자 토큰 문자열을 전달합니다.

`value.items`는 JSON 배열의 원소 목록입니다. `get`·`getAll`은 객체에서 이름으로 조회합니다. `stringValue()`·`stringUnits()`·`numberLiteral()`·`booleanValue()`는 종류별 값을 반환합니다.

UTF-8 바이트 입력은 `parseBytes(bytes)`, 공백 제거 출력은 `stringify(value, {compact: true})`입니다. 깊이 제한은 `parse(source, {maxDepth: 256})`으로 설정합니다.

직렬화에는 이 패키지의 `stringify`를 사용합니다. 일반 `JSON.stringify(value)`는 오류를 반환하여 내부 노드가 일반 객체로 출력되는 일을 방지합니다.

```sh
npm test
```

공통 검증기의 공식 예제와 기대 결과를 그대로 사용합니다.

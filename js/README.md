# JavaScript

Node.js 20 이상. 런타임 의존성 없이 ESM과 TypeScript 타입 정의를 제공합니다.

`source`는 [공식 예제](../examples/official.json)의 `input` JSON 문자열입니다.

```js
import {parse, stringify, Value} from './index.js';

const value = parse(source);
const members = value.members; // ReadonlyMap<string, Value>, 키의 첫 등장 순서
const keys = [...members.keys()];
const output = stringify(value);
```

객체는 `Value.object(map)`으로 `Map<string, Value>`를 전달하고, 배열은 `Value.array([Value, ...])`로 구성합니다. 객체 생성에는 키·값 항목을 반환하는 iterable도 사용할 수 있습니다. 문자열·숫자·불리언·null 생성은 `Value.string`, `Value.number`, `Value.boolean`, `Value.null`을 사용합니다. `Value.number`에는 숫자 토큰 문자열을 전달합니다.

`value.items`는 JSON 배열의 원소 목록입니다. `value.get(key)`와 `members.get(key)`는 해당 키의 마지막 값을 조회합니다. 같은 키를 덮어써도 첫 등장 위치는 바뀌지 않습니다. `members`는 복사본이며 수정해도 원래 `Value`에 영향을 주지 않습니다. `stringValue()`·`stringUnits()`·`numberLiteral()`·`booleanValue()`는 종류별 값을 반환합니다.

UTF-8 바이트 입력은 `parseBytes(bytes)`입니다. `stringify(value)`는 연관배열을 공백 없는 JSON으로 출력합니다. 기존 `{compact: true}` 옵션도 같은 결과를 냅니다. `value.raw`는 입력 원문 조회입니다. 깊이 제한은 `parse(source, {maxDepth: 256})`으로 설정합니다.

직렬화에는 이 패키지의 `stringify`를 사용합니다. 일반 `JSON.stringify(value)`는 오류를 반환하여 내부 노드가 일반 객체로 출력되는 일을 방지합니다.

```sh
npm test
```

공통 검증기의 공식 예제와 기대 결과를 그대로 사용합니다.

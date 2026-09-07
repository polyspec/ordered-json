<!-- doc-id: overview -->
<!-- source-sha256: 4a2e372ea9a43b03ceafdf2467eb555afa327648f19a15f1a27c9a21b217b884 -->
# ordered-json

[English](README.md)

JavaScript, Rust, Go, PHP용 JSON 라이브러리입니다. 객체는 모든 깊이에서 키의 최초 등장 순서를 유지하는 연관배열을 사용합니다. 중복 키는 해당 순서를 변경하지 않고 값을 교체합니다.

저장소는 순수 PHP와 네이티브 PHP 확장을 포함합니다. [설치 문서](docs/operations/installation.ko.md)에 정확한 식별자와 런타임 요구사항을 작성합니다.

<a id="start"></a>
## 시작

저장소 루트에서 공식 입력으로 JavaScript 구현을 실행합니다.

~~~sh
node --input-type=module <<'JS'
import {readFileSync} from 'node:fs';
import {parse, stringify} from './js/index.js';
const {cases} = JSON.parse(readFileSync('examples/official.json', 'utf8'));
const example = cases.find(example => example.id === 'document-order');
console.log(stringify(parse(example.input)));
JS
~~~

| 구현 | 사용법 |
| --- | --- |
| JavaScript 및 TypeScript 선언 | [JavaScript](js/README.ko.md) |
| Rust | [Rust](rust/README.ko.md) |
| Go | [Go](go/README.ko.md) |
| PHP | [PHP](php/README.ko.md) |
| PHP 네이티브 확장 | [네이티브 확장](php-extension/README.ko.md) |

<a id="verification"></a>
## 검증

다섯 구현은 같은 [공식 예제](examples/README.ko.md)와 공통 검증기를 사용합니다.

~~~sh
make check
~~~

필수 도구와 추가 테스트 절차는 [검증 운영 문서](docs/operations/validation.ko.md)에 작성합니다. 테스트 통과와 패키지 게시는 별도 상태입니다.

<a id="documents"></a>
## 문서

- [JSON 계약](docs/spec/json-contract.ko.md)
- [API 계약](docs/spec/api.ko.md)
- [기능 및 구현 상태](docs/features.ko.md)
- [배포 상태](docs/operations/distribution.ko.md)
- [변경 기록](CHANGELOG.ko.md)
- [문서 관리](docs/documentation-plan.ko.md)
- [개발 절차](AGENTS.ko.md)
- [요청된 비교 보고서](docs/reports/ojson-comparison.ko.md)

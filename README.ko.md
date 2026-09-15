<!-- doc-id: overview -->
<!-- source-sha256: 3e58b47a5a2372e81072b0f5f08bf549fea6d73b11b79fa65bb558e748216927 -->
# ordered-json

[English](README.md)

JavaScript, Rust, Go, PHP용 JSON 라이브러리입니다. 객체는 모든 깊이에서 문서 키 순서를 유지하는 연관배열을 사용합니다. 중복 키는 최초 위치와 마지막 값을 유지합니다.

이 저장소는 공통 명세, 공식 예제, 기대 결과, 검증기와 다섯 구현체를 모두 관리하는 단일 소스 저장소입니다. 언어별 디렉터리는 이 저장소 안에서 독립 패키지와 빌드 대상으로 동작하며, 언어별 API를 섞지 않고 하나의 리비전을 공유합니다.

<a id="start"></a>
## 시작

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
~~~

저장소 루트에서 공식 입력으로 JavaScript를 실행합니다.

~~~sh
node --input-type=module <<'JS'
import {readFileSync} from 'node:fs';
import {parse, stringify} from './js/index.js';
const {cases} = JSON.parse(readFileSync('examples/official.json', 'utf8'));
const example = cases.find(example => example.id === 'document-order');
console.log(stringify(parse(example.input)));
JS
~~~

| 패키지 | 내용 | 경로 |
| --- | --- | --- |
| JavaScript | JavaScript 및 TypeScript 선언 | `js/` |
| Rust | Rust crate | `rust/` |
| Go | Go 패키지 | `go/` |
| PHP | 순수 PHP 및 Value API | `php/` |
| PHP 확장 | PIE 메타데이터를 제공하는 네이티브 PHP 확장 | `php-extension/` |

<a id="verification"></a>
## 검증

모든 구현이 같은 [공식 예제](examples/README.ko.md)와 공통 기대값을 사용합니다. 각 패키지는 현재 체크아웃에서 독립적으로 빌드·검사되며, 루트의 `make check`는 모든 패키지를 검사합니다.

~~~sh
make check
~~~

통합 기록은 공통 계약과 모든 패키지가 포함된 하나의 리비전에 적용됩니다. 도구와 식별자는 [설치](docs/operations/installation.ko.md), 단독·추가 사례·PIE 검사는 [검증](docs/operations/validation.ko.md)을 참조합니다. 테스트와 패키지 게시는 별도로 기록합니다.

<a id="documents"></a>
## 문서

- [JSON 계약](docs/spec/json-contract.ko.md)
- [API 계약](docs/spec/api.ko.md)
- [저장소 계약](docs/spec/repositories.ko.md)
- [기능 상태](docs/features.ko.md)
- [배포 상태](docs/operations/distribution.ko.md)
- [변경 기록](CHANGELOG.ko.md)
- [문서 관리](docs/documentation-plan.ko.md)
- [개발 절차](AGENTS.ko.md)
- [요청된 비교 보고서](docs/reports/ojson-comparison.ko.md)

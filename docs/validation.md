# 검증 기록

2026-09-07, macOS arm64에서 실행했습니다.

| 구현 | 검증 환경 | 공통 판정 결과 |
| --- | --- | --- |
| JavaScript | Node.js 26.8.1 | 428 / 428 |
| Rust | rustc 1.98.1 | 428 / 428 |
| Go | Go 1.27.0 | 428 / 428 |
| 순수 PHP | PHP 8.5.10, `php -n` | 428 / 428 |
| PHP 확장 | PHP 8.5.10, C 확장 로드 | 428 / 428 |

같은 공식 예제 12개, 저장소 공통 문법 사례 98개, JSONTestSuite 318개를 [단일 검증기](../scripts/verify.py)로 검사했습니다. 각 언어는 입력을 처리하고 결과를 반환하는 어댑터만 제공합니다.

공식 기대 결과는 [examples/official.json](../examples/official.json)에 고정되어 있습니다. 추가 문법 사례는 Python 표준 JSON 디코더의 키·값 쌍 콜백 및 숫자 토큰 콜백을 이용한 독립 참조 결과와 비교합니다.

검사 범위는 유효·무효 입력 판정, 모든 깊이의 멤버와 원소 순서, 값, 직렬화, 멤버·원소 배열을 통한 재구성 후 직렬화입니다.

외부 자료: [JSONTestSuite, commit 1ef36fa01286573e846ac449e8683f8833c5b26a](https://github.com/nst/JSONTestSuite/tree/1ef36fa01286573e846ac449e8683f8833c5b26a). `i_` 입력은 UTF-8 검사와 최대 깊이 256이라는 이 구현의 정책을 적용했습니다.

```sh
python3 scripts/test.py --suite .cache/JSONTestSuite
```

이 결과는 위 환경과 사례에 대한 검증 기록입니다. 선언된 최소 런타임 버전 전체에서 실행한 결과는 아닙니다.

# ordered-json

JSON 문서에서 키가 등장한 순서대로 객체를 배열에 담고, 그 순서대로 JSON을 출력합니다. 루트·자식 객체·배열 안의 객체에 같은 규칙을 적용합니다.

문서가 `{"10":"first","2":"second"}`이면 객체 멤버 배열의 순서도 `10, 2`입니다.

| 구현 | 위치 |
| --- | --- |
| JavaScript / TypeScript 타입 정의 | [js](js/README.md) |
| Rust | [rust](rust/README.md) |
| Go | [go](go/README.md) |
| 순수 PHP | [php](php/README.md) |
| PHP 네이티브 확장(C) | [php/ext](php/ext/README.md) |

## 공통 동작

- 객체는 순서 있는 키·값 쌍의 배열로, JSON 배열은 값의 배열로 구성합니다.
- 객체와 배열의 생성 API도 전달받은 배열 순서대로 직렬화합니다.
- 중복 키를 유지합니다. `get`은 첫 번째 값을, `getAll`은 등장 순서대로 모든 값을 반환합니다.
- 숫자는 원래 JSON 토큰으로 보존하여 큰 정수·소수·지수 표기를 변경하지 않습니다.
- 수정하지 않은 값의 기본 직렬화는 원문을 반환합니다. `compact`는 문자열 밖의 JSON 공백만 제거합니다.

[RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)의 JSON 문법을 검사합니다. 주석·후행 쉼표·잘못된 숫자·잘못된 UTF-8은 거부합니다. 최대 컨테이너 중첩은 256단계이며 더 낮게 설정할 수 있습니다. BOM은 거부합니다. 이스케이프된 단독 surrogate는 손실 없이 보존하며 UTF-16 코드 단위로 조회할 수 있습니다.

## 공식 예제와 공통 검증

**공식 입력과 고정된 기대 결과는 [examples/official.json](examples/official.json) 한곳에 있습니다.** 언어별 검증 어댑터에는 별도 예제나 기대 결과가 없습니다.

[공통 검증기](scripts/verify.py)가 다섯 구현에 같은 문서를 전달하여 다음 결과를 같은 기대값과 비교합니다.

1. 모든 깊이의 객체 멤버 순서와 배열 원소 순서
2. 노드 종류와 값
3. 직렬화 결과
4. 파싱된 멤버·원소 배열로 객체·배열을 다시 구성한 뒤의 직렬화 결과

공식 예제 12개와 공통 문법 사례 98개가 저장소에 포함됩니다. 외부 JSONTestSuite를 지정하면 318개 사례를 추가로 같은 검증기에 통과시킵니다. 외부 예제의 `i_` 사례는 이 라이브러리의 UTF-8·깊이 정책에 맞춰 검사합니다.

```sh
# 최초 실행: PHP 확장을 로컬 빌드하고 다섯 구현 검증
python3 scripts/test.py --build-extension

# 이후 실행
python3 scripts/test.py

# 지정한 구현도 동일한 공식 예제와 검증기를 사용
python3 scripts/verify.py --only js
python3 scripts/verify.py --only php-native
```

[JSONTestSuite](https://github.com/nst/JSONTestSuite)까지 재현하려면:

```sh
git clone https://github.com/nst/JSONTestSuite.git .cache/JSONTestSuite
git -C .cache/JSONTestSuite checkout 1ef36fa01286573e846ac449e8683f8833c5b26a
python3 scripts/test.py --suite .cache/JSONTestSuite
```

검증 환경과 결과는 [검증 기록](docs/validation.md)에 기록합니다.

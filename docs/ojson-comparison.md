# 기존 ojson 프로젝트 검증

2026-09-07. **Python `ojson`은 중첩 객체의 문서 순서를 유지합니다. Erlang `ojson`은 키를 정렬하므로 문서 순서 보존 요구와 다릅니다.** 두 프로젝트 모두 이미 `ojson` 이름을 사용하고 있습니다.

| 대상 | 실행한 버전 | 입력 문서의 순서 | 중복 키 |
| --- | --- | --- | --- |
| [PyPI ojson](https://pypi.org/project/ojson/) | 0.1.0, Python 3.9.6 | 자식 객체와 배열 안의 객체까지 유지 | 마지막 값으로 합침 |
| [erlang-ojson](https://github.com/potatosalad/erlang-ojson) | 1.0.0, commit `5cd1de1`, Erlang/OTP 29 | 출력할 때 문자열 키를 정렬 | 이번 실행에서는 첫 번째 값만 남음 |

## 같은 공식 예제의 실제 출력

[공식 예제](../examples/official.json)의 `whitespace` 사례입니다. 아래 표는 보기 쉽게 문자열 밖의 공백만 제거한 출력입니다.

| 대상 | JSON |
| --- | --- |
| 입력 | `{"10":1,"2":{"b":2,"a":3}}` |
| Python ojson | `{"10":1,"2":{"b":2,"a":3}}` |
| Erlang ojson | `{"10":1,"2":{"a":3,"b":2}}` |

`10, 2`는 문자열 정렬 결과도 `10, 2`이므로 이 두 키만으로는 차이를 구분할 수 없습니다. 같은 문서의 자식 키 `b, a`에서 차이가 드러납니다.

`duplicate-keys` 사례도 그대로 실행했습니다.

| 대상 | JSON |
| --- | --- |
| 입력 | `{"b":1,"a":2,"b":3}` |
| Python ojson | `{"b":3,"a":2}` |
| Erlang ojson | `{"a":2,"b":1}` |

Python의 `exact-number-tokens` 출력은 `[9007199254740993, 0, 12300.0, Infinity]`였습니다. `-0`과 지수 표기가 바뀌고, `1e9999`가 기본 인코더에서 JSON 숫자 문법에 없는 `Infinity`로 출력되었습니다. Erlang은 이 입력을 거부했습니다.

## 검증 방법과 범위

[공통 검증기](../scripts/verify.py)의 입력·기대 결과 로더를 그대로 재사용했습니다. 공식 예제 12개, 저장소 문법 사례 98개, JSONTestSuite 318개로 총 428개입니다. 프로젝트별 새 예제나 새 기대값을 만들지 않았습니다.

- Python: PyPI 배포본을 내려받아 원본 `ojson.loads(bytes)`와 `ojson.dumps(value)`를 기본 옵션으로 실행했습니다. `object_pairs_hook`·숫자 파서·인코더를 교체하지 않았습니다.
- Erlang: 원본 Erlang 모듈을 직접 컴파일하여 `ojson:decode/1`과 `ojson:encode/1`을 기본 옵션으로 실행했습니다. 외부 프로젝트 소스는 수정하지 않았습니다.
- [비교 검증기](../scripts/compare_ojson.py)는 파싱 허용 여부, 파싱된 키 순서와 컨테이너 구조, 값, 출력의 JSON 문법, 출력 재파싱 결과를 따로 기록합니다.

공식 예제 결과는 다음과 같습니다. 숫자 표기까지 같아야 하는 검사와 키 순서 검사를 구분했습니다.

| 검사 | Python ojson | Erlang ojson |
| --- | --- | --- |
| 키 순서·중복 개수·컨테이너 구조 일치 | 10 / 12 | 2 / 12 |
| 값과 숫자 토큰까지 포함한 출력 트리 일치 | 9 / 12 | 2 / 12 |
| 유효한 JSON으로 출력 완료 | 11 / 12 | 10 / 12 |

Python의 첫 번째 검사 실패 두 개는 모두 중복 키 사례입니다. Erlang의 첫 번째 검사 성공 두 개는 `document-order`와 `root-scalar`입니다. 값 종류만 비교되는 스칼라 사례도 분모에 포함되므로 이 수치를 객체 순서 보존율로 일반화하지 않습니다.

추가 문법 사례에서는 Python의 `NaN`·`Infinity` 허용, Erlang의 이스케이프되지 않은 제어문자 허용도 확인했습니다. BOM·UTF-16 입력, 최대 깊이, 숫자 범위, 단독 surrogate 처리 차이도 포함되어 있어 전체 입력 판정 일치 수치를 RFC 적합성 점수로 해석하지 않습니다.

원본 소스에서도 동작을 확인했습니다. Python은 표준 JSON 디코더에 `OrderedDict`를 연결합니다. [Python 소스](https://github.com/joaoandre/ojson/blob/master/ojson/ojson.py). Erlang은 객체 출력에서 키 목록을 정렬합니다. [Erlang 소스](https://github.com/potatosalad/erlang-ojson/blob/5cd1de1a4a7622523c83d9464772b0f0926e654d/src/ojson_encoder.erl#L175).

## 재현

배포본과 소스 준비:

```sh
mkdir -p .cache/comparison
curl -L https://files.pythonhosted.org/packages/96/f0/2990e30a4b1978a104ca66fdb7aa5d0956dcf11aaf136a36e9659a699791/ojson-0.1.0.tar.gz -o .cache/comparison/ojson-0.1.0.tar.gz
tar -xzf .cache/comparison/ojson-0.1.0.tar.gz -C .cache/comparison
git clone https://github.com/potatosalad/erlang-ojson.git .cache/comparison/erlang-ojson
git -C .cache/comparison/erlang-ojson checkout 5cd1de1a4a7622523c83d9464772b0f0926e654d
```

PyPI 배포본 SHA-256: `94a1c628c0b4447680d9039c110dafe4efd6e3fdf77602b3ff543c2a278b7ec5`.

Erlang이 설치된 환경에서:

```sh
python3 scripts/compare_ojson.py --suite .cache/JSONTestSuite
```

별도 Erlang 실행 파일은 `--erl /path/to/erl`로 지정할 수 있습니다. 이번 실행에서는 Homebrew Erlang 29.0.6 바이너리를 `.cache/comparison/runtime`에 풀어 사용했습니다. 시스템 설치는 변경하지 않았습니다. 바이너리 SHA-256은 `60e6425e089726bcae182f1856b01aa88de2782b94dedf71559e8efbc5eea0f3`입니다.

원본 Erlang 코드에서 제거된 `get_stacktrace/0` API에 대한 컴파일 경고가 발생했습니다. 경고를 기록한 상태로 원본을 컴파일했으며, 이번 검증에는 `decode!/1`을 사용하지 않았습니다. 따라서 그 API의 오류 경로까지 검증한 결과는 아닙니다.

모든 사례의 판정과 공식 예제의 실제 출력은 [기계 판독 결과](ojson-comparison.json)에 있습니다. 현재 저장소의 다섯 구현도 같은 428개 사례를 다시 실행하여 모두 일치함을 확인했습니다.

<!-- doc-id: ojson-comparison -->
<!-- source-sha256: f51637e54cbf5e4fb650608261647ff4c7c508cb6e867c8d72f9a44db0a95373 -->
# ojson 비교

[English](ojson-comparison.md)

<a id="result"></a>
## 확인한 동작

요청된 비교는 Python 3.9.6의 Python ojson 0.1.0과 Erlang/OTP 29.0.6의 Erlang ojson 1.0.0, 커밋 `5cd1de1a4a7622523c83d9464772b0f0926e654d`를 사용합니다. Python은 `OrderedDict`로 재귀 문서 순서를 보존하고 최초 키 위치에 마지막 값을 사용합니다. Erlang은 인코딩할 때 문자열 키를 정렬하며 이번 실행에서는 첫 중복 값을 유지했습니다.

[공식 예제](../../examples/official.json)의 `whitespace` 사례 결과입니다. 문자열 밖의 공백은 제거했습니다.

| 입력 | Python 출력 | Erlang 출력 |
| --- | --- | --- |
| `{"10":1,"2":{"b":2,"a":3}}` | `{"10":1,"2":{"b":2,"a":3}}` | `{"10":1,"2":{"a":3,"b":2}}` |
| `{"b":1,"a":2,"b":3}` | `{"b":3,"a":2}` | `{"a":2,"b":1}` |

둘째 행은 `duplicate-keys` 사례입니다. 문자열 정렬도 `10, 2`이므로 중첩된 `b, a` 키가 정렬과 원문 순서를 구분합니다. `exact-number-tokens`에서 Python은 `[9007199254740993, 0, 12300.0, Infinity]`를 출력했습니다. 숫자 표기가 바뀌었으며 `Infinity`는 JSON 숫자가 아닙니다. Erlang은 이 입력을 거부했습니다.

<a id="method"></a>
## 방법과 결과

[compare_ojson.py](../../scripts/compare_ojson.py)는 공통 검증기의 입력과 기대 결과를 재사용합니다. 공식 예제 17개, 저장소 사례 98개, 추가 사례 318개입니다. 프로젝트별 기대값을 따로 사용하지 않습니다. 중복 키 기준은 최초 키 위치와 마지막 값입니다.

Python은 수정하지 않은 `ojson.loads(bytes)`와 `ojson.dumps(value)`를 기본 옵션으로 사용합니다. Erlang 모듈은 소스 변경 없이 컴파일하여 `ojson:decode/1`과 `ojson:encode/1`로 실행합니다. 파싱 허용 여부, 디코딩한 구조·순서, 디코딩한 값, 엄격한 JSON 출력, 출력 재파싱을 별도로 측정합니다.

| 검사 | Python | Erlang |
| --- | --- | --- |
| 공식 구조·순서 일치 | 17 / 17 | 3 / 17 |
| 숫자 토큰을 포함한 공식 디코딩 트리 | 16 / 17 | 2 / 17 |
| 숫자 토큰을 포함한 공식 인코딩 트리 | 16 / 17 | 2 / 17 |
| 공식 엄격한 JSON 출력 | 16 / 17 | 14 / 17 |
| 전체 입력 허용 판정 일치 | 417 / 433 | 402 / 433 |

Erlang의 구조 일치 사례는 `document-order`, `root-scalar`, `empty-and-null-key-overwrite`입니다. 스칼라 사례가 포함되므로 이 비율은 객체 순서 보존율이 아닙니다. Python은 `NaN`과 `Infinity`를 허용했고 Erlang은 일부 이스케이프되지 않은 제어문자를 허용했습니다. BOM, UTF-16, 깊이, 숫자 범위, 단독 surrogate 정책 차이도 입력 판정에 영향을 줍니다. 전체 수치는 RFC 적합성 점수가 아닙니다.

[Python 소스](https://github.com/joaoandre/ojson/blob/master/ojson/ojson.py)는 표준 디코더에 `OrderedDict`를 연결합니다. [고정된 Erlang 소스](https://github.com/potatosalad/erlang-ojson/blob/5cd1de1a4a7622523c83d9464772b0f0926e654d/src/ojson_encoder.erl#L175)는 객체 키를 정렬합니다. [기계 판독 결과](ojson-comparison.json)에 모든 사례의 관찰 결과와 소스 해시가 있습니다.

<a id="reproduction"></a>
## 재현

패키지와 [추가 입력](../operations/validation.ko.md#supplementary)을 준비합니다.

~~~sh
mkdir -p .cache/comparison
curl -L https://files.pythonhosted.org/packages/96/f0/2990e30a4b1978a104ca66fdb7aa5d0956dcf11aaf136a36e9659a699791/ojson-0.1.0.tar.gz -o .cache/comparison/ojson-0.1.0.tar.gz
tar -xzf .cache/comparison/ojson-0.1.0.tar.gz -C .cache/comparison
git clone https://github.com/potatosalad/erlang-ojson.git .cache/comparison/erlang-ojson
git -C .cache/comparison/erlang-ojson checkout 5cd1de1a4a7622523c83d9464772b0f0926e654d
python3 scripts/compare_ojson.py --suite .cache/JSONTestSuite
~~~

[PyPI](https://pypi.org/project/ojson/) 압축 파일의 SHA-256은 `94a1c628c0b4447680d9039c110dafe4efd6e3fdf77602b3ff543c2a278b7ec5`입니다. Erlang 런타임이 필요하며 `--erl /path/to/erl`로 특정 실행 파일을 지정합니다. 기록된 실행은 SHA-256이 `60e6425e089726bcae182f1856b01aa88de2782b94dedf71559e8efbc5eea0f3`인 격리된 Homebrew Erlang 29.0.6 압축 파일을 사용했습니다.

원본 Erlang 모듈은 제거된 `get_stacktrace/0`에 대한 컴파일 경고를 발생시켰습니다. 보고서는 경고를 소스 기준 상대 경로로 보존합니다. 이 비교는 `decode!/1`을 호출하지 않았으며 그 오류 경로를 검증하지 않습니다.

<!-- doc-id: ojson-comparison -->
# ojson comparison

[한국어](ojson-comparison.ko.md)

<a id="result"></a>
## Observed behavior

This requested comparison uses Python ojson 0.1.0 on Python 3.9.6 and Erlang ojson 1.0.0 at commit `5cd1de1a4a7622523c83d9464772b0f0926e654d` on Erlang/OTP 29.0.6. Python preserves recursive document order through `OrderedDict` and uses the last value at the first key position. Erlang sorts string keys when encoding and retained the first duplicate value in this execution.

The [official](../../examples/official.json) `whitespace` case produces these outputs, shown without whitespace outside strings:

| Input | Python output | Erlang output |
| --- | --- | --- |
| `{"10":1,"2":{"b":2,"a":3}}` | `{"10":1,"2":{"b":2,"a":3}}` | `{"10":1,"2":{"a":3,"b":2}}` |
| `{"b":1,"a":2,"b":3}` | `{"b":3,"a":2}` | `{"a":2,"b":1}` |

The second row is the `duplicate-keys` case. String sorting also produces `10, 2`, so the nested `b, a` keys distinguish sorting from source order. For `exact-number-tokens`, Python emitted `[9007199254740993, 0, 12300.0, Infinity]`: number spelling changed and `Infinity` is not a JSON number. Erlang rejected this input.

<a id="method"></a>
## Method and results

[compare_ojson.py](../../scripts/compare_ojson.py) reuses the common verifier's inputs and expectations: 17 official examples, 98 repository fixtures, and 318 supplementary cases. No separate project-specific goldens are used. The duplicate-key criterion is the first key position and the last value.

Python uses unmodified `ojson.loads(bytes)` and `ojson.dumps(value)` with default options. Erlang modules are compiled without source changes and run through `ojson:decode/1` and `ojson:encode/1`. Parsing acceptance, decoded structure/order, decoded values, strict JSON output, and reparsed output are measured separately.

| Check | Python | Erlang |
| --- | --- | --- |
| Official structure/order match | 17 / 17 | 3 / 17 |
| Official decoded tree including number tokens | 16 / 17 | 2 / 17 |
| Official encoded tree including number tokens | 16 / 17 | 2 / 17 |
| Official strict JSON outputs | 16 / 17 | 14 / 17 |
| Acceptance agreement across all inputs | 417 / 433 | 402 / 433 |

Erlang's structure matches were `document-order`, `root-scalar`, and `empty-and-null-key-overwrite`. Scalar cases are included, so these ratios are not object order preservation rates. Python accepted `NaN` and `Infinity`; Erlang accepted some unescaped controls. BOM, UTF-16, depth, number range, and lone surrogate policy differences also affect acceptance. The totals are not RFC compliance scores.

The [Python source](https://github.com/joaoandre/ojson/blob/master/ojson/ojson.py) connects the standard decoder to `OrderedDict`. The [pinned Erlang source](https://github.com/potatosalad/erlang-ojson/blob/5cd1de1a4a7622523c83d9464772b0f0926e654d/src/ojson_encoder.erl#L175) sorts object keys. [Machine results](ojson-comparison.json) contain all per-case observations and source hashes.

<a id="reproduction"></a>
## Reproduction

Prepare the packages and the [supplementary inputs](../operations/validation.md#supplementary):

~~~sh
mkdir -p .cache/comparison
curl -L https://files.pythonhosted.org/packages/96/f0/2990e30a4b1978a104ca66fdb7aa5d0956dcf11aaf136a36e9659a699791/ojson-0.1.0.tar.gz -o .cache/comparison/ojson-0.1.0.tar.gz
tar -xzf .cache/comparison/ojson-0.1.0.tar.gz -C .cache/comparison
git clone https://github.com/potatosalad/erlang-ojson.git .cache/comparison/erlang-ojson
git -C .cache/comparison/erlang-ojson checkout 5cd1de1a4a7622523c83d9464772b0f0926e654d
python3 scripts/compare_ojson.py --suite .cache/JSONTestSuite
~~~

The [PyPI](https://pypi.org/project/ojson/) archive SHA-256 is `94a1c628c0b4447680d9039c110dafe4efd6e3fdf77602b3ff543c2a278b7ec5`. An Erlang runtime is required; `--erl /path/to/erl` selects a specific executable. The recorded run used an isolated Homebrew Erlang 29.0.6 archive with SHA-256 `60e6425e089726bcae182f1856b01aa88de2782b94dedf71559e8efbc5eea0f3`.

The original Erlang modules emitted compilation warnings about removed `get_stacktrace/0`. The report retains those warnings using source-relative paths. This comparison did not call `decode!/1` and does not verify its error path.

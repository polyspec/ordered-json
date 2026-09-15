<!-- doc-id: performance-benchmarks -->
<!-- source-sha256: e904a7ecfd9a369497048261ce7b206eab954dee98a71818ec04d38496b771bd -->
# 성능 벤치마크

`run.py`는 모든 런타임에서 같은 입력 문서, 워밍업 횟수, 반복 횟수,
샘플 수를 사용해 ordered-json 구현과 일반적인 네이티브 JSON 구현을
비교합니다. Rust는 항상 release 프로필로 실행합니다.

파싱, 직렬화, 파싱 후 직렬화 시간을 측정하고 결과 digest도 확인합니다.
각 측정의 원본 샘플, median, p95, 입력 digest, 빌드 프로필, 런타임
fingerprint와 Git 작업 트리 상태를 `benchmarks/results.json`에 저장합니다.
결과 파일도 커밋하여
측정 이력과 정확한 프로토콜을 저장소에서 확인할 수 있게 합니다.

Rust 표준 라이브러리에는 JSON 파서가 없으므로 네이티브 비교 기준은
사실상 표준인 `serde_json`입니다. JavaScript, Go, PHP는 각 런타임의
네이티브 JSON API를 사용합니다. PHP는 순수 PHP 구현과 네이티브 확장도
별도로 측정합니다.

Go ordered-json 벤치마크는 명시적인 `ParseBytesBorrowed` 경로를 사용합니다.
fixture 바이트 복사를 피하며 측정 전체에서 각 입력 버퍼를 유지하고 변경하지
않습니다. 입력 버퍼를 변경할 수 있는 일반 호출자는 `ParseBytes`를 사용해야
합니다.

네이티브 측정값은 동등한 동작이라고 주장하는 값이 아니라 별도의 기준값입니다.
일반적인 네이티브 API는 객체 순서나 정확한 숫자 토큰을 보존하지 않습니다.
ordered-json 구현체끼리는 출력 digest가 일치해야 하며, 이러한 의도적인
동작 차이로 네이티브 출력 digest는 달라질 수 있습니다.

`workload.json`은 fixture의 입력 digest, 바이트 수, 노드 수, scalar 수,
최대 깊이, 워밍업, 반복 횟수, 샘플 수, 회귀 허용오차를 정의하는 기준입니다.
실행기는 입력 변경, 구현체 행 누락·중복, 잘못 보고된 입력 바이트 수를
거부합니다. 네이티브 직렬화가 달라질 수 있으므로 출력 바이트 수는 측정
결과로 기록합니다.

나노초 값은 다른 컴퓨터에서 동일할 수 없습니다. 커밋된 결과와 환경
fingerprint가 일치할 때만 비교할 수 있습니다. 같은 환경에서는 median 증가
10%와 p95 증가 30%까지 허용합니다. 각 ordered-json 구현과 metric별로
fixture 비율의 median을 사용하므로 작은 fixture 하나의 타이머 노이즈를
회귀로 판정하지 않습니다. 다른 환경은 `not-comparable`로 기록합니다.
`--check`를 사용하지 않으면 실행 결과를 현재 결과 파일에 저장합니다.
비교 가능한 실행이 허용오차를 초과하면 커밋된 기준을 보존하고 실패한
측정값을 `.cache/benchmark.current.json`에 저장합니다. 해당 측정값을 검토한
뒤에만 `--update-baseline`으로 기준을 갱신하며, 명시적인 기준 갱신은
`baseline-updated`로 기록합니다.

저장소 루트에서 다음처럼 실행합니다.

~~~sh
make benchmark
python3 benchmarks/run.py --check
python3 benchmarks/run.py --update-baseline
python3 benchmarks/run.py --iterations 10000 --warmup 1000 --samples 9
~~~

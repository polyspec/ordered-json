<!-- doc-id: performance-benchmarks -->
<!-- source-sha256: dcd2233b948486f41c0197ee975983d7a102441a6fa3739f62638a384316b6aa -->
# 성능 벤치마크

`run.py`는 모든 런타임에서 같은 입력 문서와 반복 횟수를 사용해
ordered-json 구현과 일반적인 네이티브 JSON 구현을 비교합니다.

파싱, 직렬화, 파싱 후 직렬화 시간을 측정하고 결과 digest도 확인합니다.
벤치마크 결과는 실행 환경에 따라 달라지므로 `.cache/benchmark.json`에만
저장하고 커밋하지 않습니다.

저장소 루트에서 다음처럼 실행합니다.

~~~sh
python3 benchmarks/run.py
python3 benchmarks/run.py --iterations 10000
~~~

Rust 표준 라이브러리에는 JSON 파서가 없으므로 네이티브 비교 기준은
사실상 표준인 `serde_json`입니다. JavaScript, Go, PHP는 각 런타임의
네이티브 JSON API를 사용합니다. PHP는 순수 PHP 구현과 네이티브 확장도
별도로 측정합니다.

네이티브 측정값은 동등한 동작이라고 주장하는 값이 아니라 별도의 기준값입니다.
일반적인 네이티브 API는 객체 순서나 정확한 숫자 토큰을 보존하지 않습니다.
ordered-json 구현체끼리는 출력 digest가 일치해야 하며, 이러한 의도적인
동작 차이로 네이티브 출력 digest는 달라질 수 있습니다.

`workload.json`은 fixture의 입력 바이트 수, 노드 수, scalar 수, 최대 깊이를
정의하는 기준입니다. 실행기는 입력 변경, 구현체 행 누락·중복, 잘못 보고된
입력 바이트 수를 거부합니다. 네이티브 직렬화가 달라질 수 있으므로 출력
바이트 수는 측정 결과로 기록합니다.

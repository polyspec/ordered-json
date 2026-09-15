<!-- doc-id: performance-benchmarks -->
<!-- source-sha256: 5e46e3b373ade0ad8c09a13eeb4e8411f2b2131d53e829455cafec6c01c23c18 -->
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

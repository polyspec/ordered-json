<!-- doc-id: official-examples -->
<!-- source-sha256: 5adddda24704fe97a3a005bce6ab4dd2ab91aa89f7c25fa54746ca0d698d1089 -->
# 공식 예제

[English](README.md)

<a id="format"></a>
## 공통 기대 결과

[official.json](official.json)에 모든 구현의 공통 입력과 고정 기대 결과가 있습니다. `id`는 사례 이름, `input`은 JSON 문서, `tree`는 기대 보고 트리, `compact`는 기대 연관배열 JSON 출력입니다. 검증기는 이 기대 결과를 읽으며 다시 생성하지 않습니다.

~~~text
["object", [[key, child], ...]]
["array", [child, ...]]
["string", text]
["number", token]
["boolean", flag]
["null"]
~~~

객체 항목 목록은 순서 비교를 위한 보고 형식입니다. 내부 객체는 키마다 값 하나인 연관배열이며 최초 키 위치와 마지막 값을 유지합니다. 동작은 [JSON 계약](../docs/spec/json-contract.ko.md)에 정의합니다.

<a id="verification"></a>
## 어댑터와 재구성

각 언어 어댑터는 같은 문서를 파싱하고 결과를 보고합니다. 모든 비교는 [scripts/verify.py](../scripts/verify.py)에서 수행합니다. `fixtures/` 및 선택적 추가 사례는 객체 키·값 쌍과 숫자 토큰 콜백을 사용하는 독립 표준 라이브러리 참조 결과와 비교합니다.

재구성은 각 객체의 키를 원문 순서대로 null 값과 함께 삽입하고 값을 역순으로 갱신한 뒤 라이브러리의 연관배열·배열 API로 JSON을 생성합니다. 공통 검증기는 생성된 JSON을 독립적으로 파싱하고 출력의 중복 키를 거부하며 고정된 기대 트리와 비교합니다. 키 이스케이프는 달라도 되지만 디코딩한 키, 순서, 값, 숫자 토큰은 같아야 합니다.

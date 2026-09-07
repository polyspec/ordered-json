<!-- doc-id: php-extension -->
<!-- source-sha256: b2642ae13da13b662863115c155956dbb6256d1ad393fae59b7abae8daf56182 -->
# PHP 확장

[English](README.md)

<a id="usage"></a>
## 빌드와 사용

C 확장은 엄격한 파싱과 연관배열 JSON 직렬화를 구현합니다. [공통 PHP 패키지](../php/README.ko.md)가 공개 API를 제공합니다. 확장의 `ordered_json` 버전과 PHP 런타임 버전은 별도이며 [verification.json](../docs/verification.json)에 둘 다 기록합니다.

[네이티브 설치](../docs/operations/installation.ko.md#native-php)에 따라 대상 PHP 런타임용 `modules/ordered_json.so`를 빌드합니다. [API 계약](../docs/spec/api.ko.md#php)에 `ordered_json_scan`, `ordered_json_compact`, 서술자 필드, 파서 선택을 정의합니다. Windows 설정이 포함되어 있지만 Windows 빌드는 검증되지 않았습니다.

<a id="verification"></a>
## 검증

빌드 후 저장소 루트에서 실행합니다.

~~~sh
python3 scripts/verify.py --only php-extension
~~~

어댑터는 확장을 요구하며 공통 공식 기대 결과를 사용합니다. [저장소 검사](../docs/operations/validation.ko.md)는 확장을 빌드하고 두 PHP 백엔드를 다른 구현과 비교합니다.

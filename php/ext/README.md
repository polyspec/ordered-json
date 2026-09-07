# PHP 네이티브 확장

엄격한 JSON 파서와 연관배열의 JSON 출력을 C로 구현한 PHP 확장입니다. [공통 PHP API](../README.md)와 함께 사용합니다.

현재 PHP에 맞는 개발 헤더, `phpize`, C 컴파일러, `make`가 필요합니다.

```sh
cd php/ext
phpize
./configure --enable-ordered-json
make -j2
```

빌드 결과는 `modules/ordered_json.so`입니다. 시스템 설정 변경 없이 저장소 루트에서 로드하고 검증할 수 있습니다.

```sh
python3 scripts/verify.py --only php-native
```

실제 프로그램은 다음 방식으로 실행합니다.

```sh
php -d extension=/absolute/path/to/ordered-json/php/ext/modules/ordered_json.so script.php
```

PHP 버전·플랫폼·스레드 안전 설정에 맞춰 확장을 빌드해야 합니다. 제공된 소스는 PHP 8.2 이상 API를 대상으로 하며 실제 검증 환경은 [검증 기록](../../docs/validation.md)을 확인합니다.

저수준 함수 `ordered_json_scan($source, $maxDepth = 256)`은 노드 종류, UTF-8 바이트 범위, 객체의 `members` 연관배열, 첫 키 토큰의 `keys` 메타데이터, 배열 원소 목록, 문자열의 UTF-16 단위를 반환합니다. `members`는 키의 첫 등장 순서를 유지하며 마지막 값을 담습니다. `ordered_json_compact($source, $maxDepth = 256)`는 문법 검사 후 이 연관배열을 공백 없는 JSON으로 출력합니다. 일반 사용은 공통 `OrderedJson\Value` API를 권장합니다.

<!-- doc-id: installation -->
<!-- source-sha256: 557bca0ba504d2a45c3f05eee3494716a0f0e6db7d6be42b364d0cae4ddb49ef -->
# 설치와 실행

[English](installation.md)

<a id="requirements"></a>
## 요구사항과 식별자

| 구성 요소 | 선언된 요구사항 | 현재 식별자 | 메타데이터 |
| --- | --- | --- | --- |
| JavaScript | Node.js >= 20, ESM | `ordered-json`, 0.1.0 | [package.json](../../js/package.json) |
| Rust | Rust >= 1.70, edition 2021 | `ordered-json`, 0.1.0 | [Cargo.toml](../../rust/Cargo.toml) |
| Go | Go >= 1.22 | `github.com/ordered-json/ordered-json/go` 모듈, `orderedjson` 패키지 | [go.mod](../../go/go.mod) |
| PHP | PHP >= 8.2, JSON 및 PCRE 확장 | `ordered-json/ordered-json`, `OrderedJson` 네임스페이스 | [composer.json](../../php/composer.json) |
| 네이티브 PHP | 일치하는 PHP 개발 헤더, C 컴파일러, phpize, make | `ordered_json` 확장, 0.1.0 | [확장 소스](../../php/ext/ordered_json.c) |
| 저장소 검사 | Python >= 3.9, Git, make, 위 런타임 전체 | `make check` | [검증](validation.ko.md) |

선언된 최소 버전이며 모든 최소 버전에서 테스트했다는 의미는 아닙니다. 실제 버전은 [verification.json](../verification.json)에 기록합니다. JavaScript, Rust, Go는 외부 런타임 라이브러리에 의존하지 않습니다.

<a id="checkout"></a>
## 소스 체크아웃

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
~~~

로컬 모듈 또는 소스 디렉터리를 사용합니다. 레지스트리 설치와 게시는 검증되지 않았습니다. [배포](distribution.ko.md)를 확인합니다.

- JavaScript: `js/index.js`에서 가져옵니다. TypeScript 선언은 `js/index.d.ts`에 있습니다.
- Rust: `path`가 `rust/`를 지정하는 로컬 Cargo 의존성을 설정합니다.
- Go: `github.com/ordered-json/ordered-json/go` 모듈의 로컬 `replace`가 `go/`를 지정하도록 설정합니다.
- PHP: `php/src/OrderedJson.php`를 require하거나 `php/`를 Composer path 저장소로 사용합니다.

<a id="native-php"></a>
## 네이티브 PHP

확장을 로드할 PHP 런타임에 맞춰 빌드합니다.

~~~sh
cd php/ext
phpize --clean
phpize
./configure --enable-ordered-json
make -j2
~~~

현재 Unix 빌드는 `php/ext/modules/ordered_json.so`를 생성합니다. 저장소 루트에서는 다음과 같이 실행합니다.

~~~sh
php -n -d extension="$PWD/php/ext/modules/ordered_json.so" script.php
~~~

`script.php`는 확장을 사용하는 임의의 PHP 스크립트입니다. `php -n`은 php.ini를 무시하며 필수 내장 JSON 및 PCRE 지원은 사용할 수 있어야 합니다. 소스에는 `config.w32`가 포함돼 있지만 Windows 빌드는 검증되지 않았습니다.

공통 PHP API와 파서 선택 규칙은 [API 계약](../spec/api.ko.md#php)에 정의합니다. 네이티브 소스나 PHP 빌드 설정을 변경하면 모듈을 다시 빌드합니다.

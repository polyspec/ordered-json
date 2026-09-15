<!-- doc-id: installation -->
<!-- source-sha256: 8b9a1c98cb576694632703823d994a68f382a42188b11226dab3b084a34056fd -->
# 설치와 실행

[English](installation.md)

<a id="requirements"></a>
## 요구사항과 식별자

| 구성 요소 | 선언된 요구사항 | 현재 식별자 | 메타데이터 |
| --- | --- | --- | --- |
| JavaScript | Node.js >= 20, ESM | `ordered-json`, 0.1.0 | [package.json](https://github.com/polyspec/ordered-json/blob/main/js/package.json) |
| Rust | Rust >= 1.70, edition 2021 | `ordered-json`, 0.1.0 | [Cargo.toml](https://github.com/polyspec/ordered-json/blob/main/rust/Cargo.toml) |
| Go | Go >= 1.22 | `github.com/polyspec/ordered-json/go` 모듈, `orderedjson` 패키지 | [go.mod](https://github.com/polyspec/ordered-json/blob/main/go/go.mod) |
| PHP | PHP >= 8.2, JSON 및 PCRE 확장 | `ordered-json/ordered-json`, `OrderedJson` 네임스페이스 | [composer.json](https://github.com/polyspec/ordered-json/blob/main/php/composer.json) |
| 네이티브 PHP | 일치하는 PHP 개발 헤더, C 컴파일러, phpize, make | `ordered_json` 확장, 0.1.0 | [확장 소스](https://github.com/polyspec/ordered-json/blob/main/php-extension/src/ordered_json.c) |
| 저장소 검사 | Python >= 3.9, Git, make, 위 런타임 전체 | `make check` | [검증](validation.ko.md) |

선언된 최소 버전이며 모든 최소 버전에서 테스트했다는 의미는 아닙니다. 실제 버전은 [verification.json](../verification.json)에 기록합니다. JavaScript, Rust, Go는 외부 런타임 라이브러리에 의존하지 않습니다.

<a id="checkout"></a>
## 소스 체크아웃

~~~sh
git clone https://github.com/polyspec/ordered-json.git
cd ordered-json
~~~

복제본에는 모든 구현 패키지가 포함됩니다. 패키지 디렉터리 또는 게시된 패키지가 준비된 경우 게시 패키지를 사용합니다. 레지스트리 설치와 게시는 검증되지 않았습니다. [배포](distribution.ko.md)를 확인합니다.

- JavaScript: `js/index.js`에서 가져옵니다. TypeScript 선언은 `js/index.d.ts`에 있습니다.
- Rust: `path`가 `rust/`를 지정하는 로컬 Cargo 의존성을 설정합니다.
- Go: `github.com/polyspec/ordered-json/go` 모듈의 로컬 `replace`가 `go/`를 지정하도록 설정합니다.
- PHP: `php/src/OrderedJson.php`를 require하거나 `php/`를 Composer path 저장소로 사용합니다.

<a id="native-php"></a>
## 네이티브 PHP

확장을 로드할 PHP 런타임에 맞춰 빌드합니다.

~~~sh
cd php-extension/src
if test -f Makefile; then make distclean; fi
phpize --clean
phpize
./configure --enable-ordered-json
make -j2
~~~

현재 Unix 빌드는 `php-extension/src/modules/ordered_json.so`를 생성합니다. 저장소 루트에서는 다음과 같이 실행합니다.

~~~sh
php -n -d extension="$PWD/php-extension/src/modules/ordered_json.so" application.php
~~~

`application.php`는 호출자의 애플리케이션입니다. `php -n`은 php.ini를 무시하며 필수 내장 JSON 및 PCRE 지원은 사용할 수 있어야 합니다. 소스에는 `config.w32`가 포함돼 있지만 Windows와 ZTS 빌드는 검증되지 않았습니다. PIE에는 `pkg-config`를 포함한 빌드 도구가 필요하며 macOS의 Homebrew 패키지는 `pkgconf`입니다. 재현 가능한 PIE 빌드와 공통 검증 절차는 [PIE 산출물 검사](validation.ko.md#pie)를 참조합니다.

macOS의 configure는 명시된 `MACOSX_DEPLOYMENT_TARGET`을 유지하며 값이 없으면 `CFLAGS`의 대상 플래그를 포함한 현재 C 컴파일러에서 구합니다. 로드 가능한 번들은 최신 대상에서 동적 심볼 조회를 사용하고 사용하지 않는 동적 라이브러리 단일 모듈 플래그 검사를 제외합니다.

공통 PHP API와 파서 선택 규칙은 [API 계약](../spec/api.ko.md#php)에 정의합니다. 네이티브 소스나 PHP 빌드 설정을 변경하면 모듈을 다시 빌드합니다.

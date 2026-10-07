<!-- doc-id: installation -->
<!-- source-sha256: 4da44ffa72c3056ff21ed202085e9c67f1414826cd7e5e8df33b8cc3bf9d4c5b -->
# 설치와 실행

[English](installation.md)

<a id="requirements"></a>
## 요구사항과 식별자

| 구성 요소 | 선언된 요구사항 | 현재 식별자 | 메타데이터 |
| --- | --- | --- | --- |
| JavaScript | Node.js >= 20, ESM | `@polyspec/ordered-json`, 0.0.3 | [package.json](https://github.com/polyspec/ordered-json/blob/main/js/package.json) |
| Rust | Rust >= 1.71, edition 2021 | `polyspec-ordered-json`, 0.0.3 | [Cargo.toml](https://github.com/polyspec/ordered-json/blob/main/rust/Cargo.toml) |
| Go | Go >= 1.22 | `github.com/polyspec/ordered-json/go` 모듈, `orderedjson` 패키지 | [go.mod](https://github.com/polyspec/ordered-json/blob/main/go/go.mod) |
| PHP | PHP >= 8.2, JSON 및 PCRE 확장 | `polyspec/ordered-json`, `Polyspec\OrderedJson` 네임스페이스 | [composer.json](https://github.com/polyspec/ordered-json/blob/main/php/composer.json) |
| 네이티브 PHP | 일치하는 PHP 개발 헤더, C 컴파일러, phpize, make | `ordered_json` 확장, 0.0.3 | [확장 소스](https://github.com/polyspec/ordered-json/blob/main/php-extension/src/ordered_json.c) |
| 저장소 검사 | 고정된 Python, Node.js, Rust, Go, npm release, Git, make, 위 PHP | `make tools`, `make check` | [검증](validation.ko.md) |

저장소 검사는 추적 파일이 고정한 정확한 release로 실행합니다. Node.js는 `.node-version`, Rust는 `rust-toolchain.toml`, Go는 `go/go.mod`의 `toolchain` 줄, Python은 `.python-version`에 minor release로, PHP는 `.php-version`에 minor release로, npm은 `package.json`의 `packageManager` 필드에 registry tarball의 SHA-512와 함께 고정합니다. `make tools`는 그 Rust toolchain을 rustup으로 설치하고, 그 npm을 Git이 무시하는 checkout의 `.cache/tools/npm`에 설치합니다. 기계의 npm은 사용하지도 바꾸지도 않습니다. `make toolchains-check`는 모든 도구를 고정값과 비교하고, 검사의 각 진입점도 첫 단계 전에 같은 비교를 하며, 다른 도구마다 기대 버전과 실제 버전 또는 명령의 오류를 밝히며 실패합니다. `GOTOOLCHAIN=local`과 `RUSTUP_AUTO_INSTALL=0`은 실행 중에 go와 rustup이 다른 toolchain을 내려받거나 설치하지 못하게 하고, 모든 cargo 명령은 `--locked`를 사용합니다.

표는 선언된 최소 버전이며 모든 최소 버전에서 테스트했다는 의미는 아닙니다. 실제 버전은 commit을 검증하는 실행의 [기록](validation.ko.md#records)에 기록합니다. JavaScript, Rust, Go는 외부 런타임 라이브러리에 의존하지 않습니다.

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

<a id="release-assets"></a>
## 릴리스 asset

GitHub Release `vX.Y.Z`마다 `polyspec-ordered-json-X.Y.Z.tgz`, `polyspec-ordered-json-X.Y.Z.zip`, `polyspec-ordered-json-extension-X.Y.Z.zip`이 있습니다. 각 archive는 자기 package의 manifest를 바꾸지 않고 담습니다. `js/`의 `package.json`, `php/`와 `php-extension/`의 `composer.json`이며, 모두 `version` X.Y.Z를 선언하고 `repositories`와 `@dev`가 없습니다.

npm은 tarball을 경로로 설치합니다.

~~~sh
mkdir app && cd app
npm init -y
npm install ./polyspec-ordered-json-X.Y.Z.tgz
~~~

Composer는 zip들을 담은 디렉터리인 artifact repository에서 zip을 설치합니다. `composer.json` 옆의 `assets/`에 zip이 있을 때:

~~~json
{
  "repositories": [
    {"type": "artifact", "url": "assets"},
    {"packagist.org": false}
  ],
  "require": {"polyspec/ordered-json": "X.Y.Z"}
}
~~~

~~~sh
composer install
~~~

Composer는 두 zip을 모두 읽습니다. type이 `php-ext`인 package `polyspec/ordered-json-extension`은 설치하지 않으며, PIE가 빌드하고 설치합니다([네이티브 PHP](#native-php)).

이 저장소의 package는 다른 package에 의존하지 않으므로 저장소에는 npm workspaces와 비공개 개발 manifest가 없습니다. 루트의 `package.json`과 `composer.json`은 checkout에서 설치하도록 `js/`, `php/`와 같은 package를 같은 `version`으로 선언하며 `repositories`가 없습니다. `scripts/tests/test_release.py`는 archive를 빌드하고, 저장소 밖의 임시 디렉터리에서 `scripts/tests/install`의 커밋된 consumer fixture로 consumer처럼 설치합니다. fixture는 tarball에 릴리스 이름으로 의존하는 `package.json`과 그 `package-lock.json`, zip의 artifact repository에서 library를 요구하는 `composer.json`과 그 `composer.lock`입니다. 각 lock은 archive를 hash로 고정합니다. `npm ci`는 빈 cache와 도달할 수 없는 registry를 가리키는 scope `@polyspec`로, `composer install`은 빈 `COMPOSER_HOME`과 `COMPOSER_CACHE_DIR`로 실행합니다. `make install-fixtures`는 작업 tree의 archive로 fixture와 lock을 쓰며, package나 버전이 바뀌면 실행합니다.

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
php -n -d extension="$PWD/php-extension/src/modules/ordered_json.so" script.php
~~~

`script.php`는 확장을 사용하는 임의의 PHP 스크립트입니다. `php -n`은 php.ini를 무시하며 필수 내장 JSON 및 PCRE 지원은 사용할 수 있어야 합니다. 소스에는 `config.w32`가 포함돼 있지만 Windows와 ZTS 빌드는 검증되지 않았습니다. PIE에는 `pkg-config`를 포함한 빌드 도구가 필요하며 macOS의 Homebrew 패키지는 `pkgconf`입니다. 재현 가능한 PIE 빌드와 공통 검증 절차는 [PIE 산출물 검사](validation.ko.md#pie)를 참조합니다.

macOS의 configure는 명시된 `MACOSX_DEPLOYMENT_TARGET`을 유지하며 값이 없으면 `CFLAGS`의 대상 플래그를 포함한 현재 C 컴파일러에서 구합니다. 로드 가능한 번들은 최신 대상에서 동적 심볼 조회를 사용하고 사용하지 않는 동적 라이브러리 단일 모듈 플래그 검사를 제외합니다.

공통 PHP API와 파서 선택 규칙은 [API 계약](../spec/api.ko.md#php)에 정의합니다. 네이티브 소스나 PHP 빌드 설정을 변경하면 모듈을 다시 빌드합니다.
